"""Verified project-party matching shared by the public source derivative."""
from __future__ import annotations
from typing import Any
from fastapi import HTTPException

def is_project_homeowner(caller: Any, quote: dict) -> bool:
    """Match a verified auth subject, or a nonempty verified legacy email."""
    if getattr(caller,'role',None)!='homeowner':return False
    subject=str(getattr(caller,'id','') or '')
    expected=str(quote.get('homeowner_auth_id') or '')
    if subject and expected and subject==expected:return True
    email=str(getattr(caller,'email','') or '').strip().casefold()
    expected_email=str(quote.get('homeowner_email') or '').strip().casefold()
    return bool(email and expected_email and email==expected_email)

def project_party(caller: Any, quote: dict) -> tuple[str,str]:
    """Resolve the sender from verified identity and this quote's participants."""
    contractor=str(getattr(caller,'contractor_id','') or '')
    if getattr(caller,'role',None)=='contractor' and contractor and contractor==str(quote.get('contractor_id') or ''):
        return 'contractor',contractor
    if is_project_homeowner(caller,quote):return 'homeowner',str(caller.id)
    raise HTTPException(status_code=403,detail='Project access required')
