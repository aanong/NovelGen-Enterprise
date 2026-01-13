from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from src.db.models import ReferenceMaterial, Novel
from src.utils import get_embedding

class ReferenceService:
    @staticmethod
    def add_reference(db: Session, novel_id: Optional[int], data: Dict[str, Any]) -> ReferenceMaterial:
        # Check novel existence if novel_id is provided
        if novel_id is not None:
            novel = db.query(Novel).filter(Novel.id == novel_id).first()
            if not novel:
                raise ValueError(f"Novel with ID {novel_id} not found")
        
        # Check duplicate
        query = db.query(ReferenceMaterial).filter(ReferenceMaterial.title == data["title"])
        if novel_id is not None:
            query = query.filter(ReferenceMaterial.novel_id == novel_id)
        else:
            query = query.filter(ReferenceMaterial.novel_id.is_(None))
            
        existing = query.first()
        
        if existing:
            raise ValueError(f"Reference material with title '{data['title']}' already exists")
        
        # Generate embedding
        try:
            embedding = get_embedding(data["content"])
        except Exception as e:
            raise RuntimeError(f"Failed to generate embedding: {str(e)}")
        
        # Create
        ref_material = ReferenceMaterial(
            title=data["title"],
            content=data["content"],
            source=data.get("source"),
            category=data.get("category"),
            tags=data.get("tags") or [],
            novel_id=novel_id,
            embedding=embedding
        )
        
        db.add(ref_material)
        db.commit()
        db.refresh(ref_material)
        return ref_material

    @staticmethod
    def batch_add_references(db: Session, novel_id: Optional[int], references: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Check novel existence if novel_id is provided
        if novel_id is not None:
            novel = db.query(Novel).filter(Novel.id == novel_id).first()
            if not novel:
                raise ValueError(f"Novel with ID {novel_id} not found")
        
        created_refs = []
        errors = []
        
        for ref_data in references:
            # Check duplicate
            query = db.query(ReferenceMaterial).filter(ReferenceMaterial.title == ref_data["title"])
            if novel_id is not None:
                query = query.filter(ReferenceMaterial.novel_id == novel_id)
            else:
                query = query.filter(ReferenceMaterial.novel_id.is_(None))
                
            existing = query.first()
            
            if existing:
                errors.append(f"'{ref_data['title']}' already exists")
                continue
            
            try:
                # Generate embedding
                embedding = get_embedding(ref_data["content"])
                
                # Create
                ref_material = ReferenceMaterial(
                    title=ref_data["title"],
                    content=ref_data["content"],
                    source=ref_data.get("source"),
                    category=ref_data.get("category"),
                    tags=ref_data.get("tags") or [],
                    novel_id=novel_id,
                    embedding=embedding
                )
                
                db.add(ref_material)
                created_refs.append(ref_material)
            except Exception as e:
                errors.append(f"Failed to create '{ref_data['title']}': {str(e)}")
        
        db.commit()
        
        for ref in created_refs:
            db.refresh(ref)
            
        return {
            "created": created_refs,
            "errors": errors,
            "message": f"Created {len(created_refs)} references, {len(errors)} errors"
        }

    @staticmethod
    def get_references(db: Session, novel_id: Optional[int], skip: int = 0, limit: int = 100, 
                      category: Optional[str] = None, search: Optional[str] = None) -> List[ReferenceMaterial]:
        if novel_id is not None:
            query = db.query(ReferenceMaterial).filter(ReferenceMaterial.novel_id == novel_id)
        else:
            query = db.query(ReferenceMaterial).filter(ReferenceMaterial.novel_id.is_(None))
        
        if category:
            query = query.filter(ReferenceMaterial.category == category)
            
        if search:
            query = query.filter(ReferenceMaterial.title.contains(search) | ReferenceMaterial.content.contains(search))
            
        return query.order_by(ReferenceMaterial.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_reference(db: Session, reference_id: int) -> Optional[ReferenceMaterial]:
        return db.query(ReferenceMaterial).filter(ReferenceMaterial.id == reference_id).first()

    @staticmethod
    def update_reference(db: Session, reference_id: int, data: Dict[str, Any]) -> Optional[ReferenceMaterial]:
        ref = db.query(ReferenceMaterial).filter(ReferenceMaterial.id == reference_id).first()
        if not ref:
            return None
        
        # If content changes, regenerate embedding
        if "content" in data and data["content"] != ref.content:
            try:
                data["embedding"] = get_embedding(data["content"])
            except Exception as e:
                raise RuntimeError(f"Failed to generate embedding: {str(e)}")
        
        for key, value in data.items():
            setattr(ref, key, value)
            
        db.commit()
        db.refresh(ref)
        return ref

    @staticmethod
    def delete_reference(db: Session, reference_id: int) -> bool:
        ref = db.query(ReferenceMaterial).filter(ReferenceMaterial.id == reference_id).first()
        if not ref:
            return False
        
        db.delete(ref)
        db.commit()
        return True
