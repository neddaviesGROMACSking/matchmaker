from pydantic import BaseModel
from typing import Optional, List, Any

class ScopusSearchResult(BaseModel):
    eid:Optional[str]
    doi: Optional[str]
    pii: Optional[str]
    pubmed_id: Optional[str]
    title: Optional[str]
    subtype: Optional[str]
    subtypeDescription: Optional[str]
    creator: Optional[str]
    afid: Optional[str]
    affilname: Optional[str]
    affiliation_city: Optional[str]
    affiliation_country: Optional[str]
    author_count: Optional[str]
    author_names: Optional[str]
    author_ids: Optional[str]
    author_afids: Optional[str]
    coverDate: Optional[str]
    coverDisplayDate: Optional[str]
    publicationName: Optional[str]
    issn: Optional[str]
    source_id: Optional[str]
    eIssn: Optional[str]
    aggregationType: Optional[str]
    volume: Optional[str]
    issueIdentifier: Optional[str]
    article_number: Optional[str]
    pageRange: Optional[str]
    description: Optional[str]
    authkeywords: Optional[str]
    citedby_count: Optional[str]
    openaccess: Optional[str]
    fund_acr: Optional[str]
    fund_no: Optional[str]
    fund_sponsor: Optional[str]


# Priority Fields
class ScopusSearchQuery(BaseModel):
    _all: str
    #Id
    doi: str
    pmid: str
    #Title
    title: str
    #Author
    au_id:str
    auth:str
    author_name:str
    #Journal
    srctitle: str
    publisher: str
    #Abstract
    _abs: str
    #Affiliation
    affil: str
    af_id: str
    #Keywords
    key: str
    authkey: str
    #Year
    pubyear: int
    #Areas
    subjarea: str
    #References
    ref: str
"""
# Candidate Fields
class ScopusSearchQuery(BaseModel):
    _all: str
    #Affiliation
    affil: str
    affilcity: str
    affilcountry: str
    affilorg: str
    af_id: str

    #Author
    au_id:str
    auth:str
    authcollab: str
    authfirst: str
    authlastname: str
    author_name:str
    firstauth:str

    #Paper id
    doi: str
    pmid: str
    isbn: str
    issn: str

    #Journal
    exactsrctitle: str
    srctitle: str
    srctype: str
    publisher: str

    #Year
    pubyear: int

    #Title
    title: str

    #Abstract
    _abs: str

    #Keywords
    key: str
    authkey: str
    indexterms: str
    tradename: str
    chemname: str

    #Combined
    title_abs_key: str
    title_abs_key_auth: str
    #References
    ref: str
    refartnum: str
    refauth: str
    refpage: str
    refpagefirst: str
    refpubyear: str
    refsrctitle: str
    reftitle: str

    #Areas
    subjarea: str
"""


"""
Other fields:
    artnum
    casregnumber
    chem
    coden
    conf
    confloc
    confname
    confsponsors
    doctype
    edfirst
    editor
    edlastname
    eissn
    fund_acr
    fund_no
    fund_sponsor
    issnp
    issue
    language
    manufacturer
    openaccess
    pagefirst
    pagelast
    pages
    pubstage
    seqbank
    seqnumber
    volume
    website
"""
"""
All fields:
    _abs
    affil
    affilcity
    affilcountry
    affilorg
    af_id
    _all
    artnum
    au_id
    auth
    authcollab
    authfirst
    authkey
    authlastname
    author_name
    casregnumber
    chem
    chemname
    coden
    conf
    confloc
    confname
    confsponsors
    doctype
    doi
    edfirst
    editor
    edlastname
    eissn
    exactsrctitle
    firstauth
    fund_acr
    fund_no
    fund_sponsor
    indexterms
    isbn
    issn
    issnp
    issue
    key
    language
    manufacturer
    openaccess
    pagefirst
    pagelast
    pages
    pmid
    publisher
    pubstage
    pubyear
    ref
    refartnum
    refauth
    refpage
    refpagefirst
    refpubyear
    refsrctitle
    reftitle
    seqbank
    seqnumber
    srctitle
    srctype
    subjarea
    title
    title_abs_key
    title_abs_key_auth
    tradename
    volume
    website
"""

class AuthorSearchResult(BaseModel):
    eid: str
    surname: Optional[str]
    initials: Optional[str]
    givenname: Optional[str]
    affiliation: Optional[str]
    documents: int
    affiliation_id: str
    city: Optional[str]
    country: Optional[str]
    areas: List[str]

class AuthorSearchQuery(BaseModel):
    #Affiliation
    af_id: str
    affil: str
    #Id
    au_id: str
    #Name
    authfirst: str
    authlastname: str
    #area
    subjarea: str


class AffiliationSearchResult(BaseModel):
    eid: str
    name: str
    variant: Optional[str]
    documents: int
    city: str
    country: str
    parent: str

class AffiliationSearchQuery(BaseModel):
    afid: str
    affil: str
