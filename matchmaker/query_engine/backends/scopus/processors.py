from pydantic import BaseModel
from typing import Optional, List, Tuple

class ProcessedScopusSearchResult(BaseModel):
    class Name(BaseModel):
        surname: str
        given_names: Optional[str] = None
    scopus_id: str
    doi: Optional[str] 
    pubmed_id: Optional[str] 
    title: str 
    author_names: Optional[List[Name]]
    author_ids: Optional[List[str]]
    author_afids: Optional[List[List[str]] ]
    description: Optional[str] 
    authkeywords: Optional[List[str]] 
    citedby_count: Optional[str] 
    publicationName: str 
    year: int 
    source_id: Optional[str]
    afids: Optional[List[str]]
    affilnames: Optional[List[str]]
    affilprocs: Optional[List[List[Tuple[str,str]]]]

"""
    pii: Optional[str]
    subtype: Optional[str]
    subtypeDescription: Optional[str]
    creator: Optional[str]
    #author_count: Optional[str]
    coverDisplayDate: Optional[str]
    issn: Optional[str]
    eIssn: Optional[str]
    aggregationType: Optional[str]
    volume: Optional[str]
    issueIdentifier: Optional[str]
    article_number: Optional[str]
    pageRange: Optional[str]
    openaccess: Optional[str]
    fund_acr: Optional[str]
    fund_no: Optional[str]
    fund_sponsor: Optional[str]
"""