"""写作文档 CRUD 服务"""

import json
from typing import Optional
from sqlalchemy import desc
from sqlalchemy.orm import Session
from app.models.writing import WritingDocument


def list_documents(db: Session, document_type: Optional[str] = None):
    """列出所有写作文档"""
    q = db.query(WritingDocument)
    if document_type:
        q = q.filter(WritingDocument.document_type == document_type)
    return q.order_by(desc(WritingDocument.updated_at)).all()


def get_document(db: Session, doc_id: str) -> Optional[WritingDocument]:
    """获取单个文档"""
    return db.get(WritingDocument, doc_id)


def create_document(db: Session, title: str = "无标题文档", content: str = "",
                    document_type: str = "paper", linked_paper_ids: list = None) -> WritingDocument:
    """创建新文档"""
    doc = WritingDocument(
        title=title,
        content=content,
        document_type=document_type,
        linked_paper_ids=json.dumps(linked_paper_ids or []),
        word_count=len(content),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def update_document(db: Session, doc_id: str, **kwargs) -> Optional[WritingDocument]:
    """更新文档字段"""
    doc = db.get(WritingDocument, doc_id)
    if not doc:
        return None
    for key, value in kwargs.items():
        if hasattr(doc, key) and value is not None:
            if key == "linked_paper_ids" and isinstance(value, list):
                value = json.dumps(value)
            setattr(doc, key, value)
    # Auto-update word count when content changes
    if "content" in kwargs:
        doc.word_count = len(kwargs["content"])
    db.commit()
    db.refresh(doc)
    return doc


def delete_document(db: Session, doc_id: str) -> bool:
    """删除文档"""
    doc = db.get(WritingDocument, doc_id)
    if not doc:
        return False
    db.delete(doc)
    db.commit()
    return True


def link_paper(db: Session, doc_id: str, paper_id: str) -> Optional[WritingDocument]:
    """关联文献到文档"""
    doc = db.get(WritingDocument, doc_id)
    if not doc:
        return None
    ids = json.loads(doc.linked_paper_ids or "[]")
    if paper_id not in ids:
        ids.append(paper_id)
        doc.linked_paper_ids = json.dumps(ids)
        db.commit()
        db.refresh(doc)
    return doc


def unlink_paper(db: Session, doc_id: str, paper_id: str) -> Optional[WritingDocument]:
    """取消文献关联"""
    doc = db.get(WritingDocument, doc_id)
    if not doc:
        return None
    ids = json.loads(doc.linked_paper_ids or "[]")
    if paper_id in ids:
        ids.remove(paper_id)
        doc.linked_paper_ids = json.dumps(ids)
        db.commit()
        db.refresh(doc)
    return doc
