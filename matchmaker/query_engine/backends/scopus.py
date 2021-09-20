from pydantic import BaseModel
from typing import List, Union, Literal, Optional, Any

from matchmaker.query_engine.query_types import PaperSearchQuery, \
        AuthorSearchQuery, PaperDetailsQuery, AuthorDetailsQuery, CoauthorQuery
from matchmaker.query_engine.data_types import PaperData, AuthorData
from matchmaker.query_engine.slightly_less_abstract import SlightlyLessAbstractQueryEngine
from matchmaker.query_engine.backend import Backend

from urllib.parse import quote_plus
import xml.etree.ElementTree as xml_parse
import xmltodict
import requests
#from atoma import parse_atom_bytes
import json
#https://dev.elsevier.com/sc_search_tips.html
class ScopusSearchQuery(BaseModel):
    all: str
    affil: str
    af_id: str
    au_id: str
    auth: str
    authcollab: str
    doi: str
    pmid: str
    publisher: str
    pubyear: str
    ref: str
    scrtitle: str
    title: str

class ScopusPaperData(BaseModel):
    pass

class Affiliation(BaseModel):
    afid: str
    name: str
    varients: List[str]
    city: str
    country: str

class ScopusSearchResult(BaseModel):
    class Author(BaseModel):
        authid: str
        authname: str
        surname: str
        initials: str
        given_name: Optional[str] = None

    title: str
    creator: str
    scopus_id: str
    publication: str
    cover_date: str
    cover_display_date: str
    authors: List[Author]
    description: str
    affiliations: List[Affiliation]
    keywords: Optional[List[str]] = None

def test_scopus_search():
    #https://api.elsevier.com/content/search/scopus?start=5&count=5&query=heart&view=COMPLETE&ver=new
    test_data = requests.get('https://dev.elsevier.com/payloads/search/scopusSearchResp.json').text

    dict_struc = json.loads(test_data)
    results = dict_struc['search-results']['entry']
    new_results = []
    for result in results:
        scopus_id = result['dc:identifier']
        title = result['dc:title']
        creator = result['dc:creator']
        publication = result['prism:publicationName']
        cover_date = result['prism:coverDate']
        cover_display_date = result['prism:coverDisplayDate']
        if 'prism:doi' in result:
            doi = result['prism:doi']
        description = result['dc:description']

        proc_affiliations = []
        affiliations = result['affiliation']
        for affiliation in affiliations:
            afid = affiliation['afid']
            affiliation_name = affiliation['affilname']
            affiliation_varients = [i['$'] for i in affiliation['name-variant']]
            affiliation_city = affiliation['affiliation-city']
            affiliation_country = affiliation['affiliation-country']
            proc_affiliations.append({
                'afid': afid,
                'name': affiliation_name,
                'varients': affiliation_varients,
                'city': affiliation_city,
                'country': affiliation_country
            })
        
        proc_authors = []
        authors = result['author']
        for author in authors:
            authid = author['authid']
            authname = author['authname']
            surname = author['surname']
            if 'given-name' in author:
                given_name = author['given-name']
            else:
                given_name = None
            initials = author['initials']
            proc_authors.append({
                'authid': authid,
                'authname': authname,
                'surname': surname,
                'given_name': given_name,
                'initials': initials
            })
            #afid seems unreliable here
        if 'authkeywords' in result:
            keywords = result['authkeywords']
        else:
            keywords = None
        new_results.append(ScopusSearchResult.parse_obj({
            'title': title,
            'creator': creator,
            'scopus_id': scopus_id,
            'publication': publication,
            'cover_date': cover_date,
            'cover_display_date': cover_display_date,
            'authors': proc_authors,
            'description': description,
            'affiliations': proc_affiliations
        }))
    return new_results

class ScopusAuthorQuery(BaseModel):
    institution_id: str

class ScopusAuthorData(BaseModel):
    auth_id: str
    name: str

def test_scopus_get_authors_from_institution():
    #https://api.elsevier.com/analytics/scival/author/institutionId/508175?httpAccept=application/json&offset=0&yearRange=5yrs
    test_data = requests.get('https://dev.elsevier.com/payloads/scival/authorsByInstitutionResp.json').text
    dict_struc = json.loads(test_data)
    authors = dict_struc['authors']
    #print(authors)
    new_authors = []
    for author in authors:
        new_authors.append(ScopusAuthorData(
            auth_id = author['id'],
            name = author['name']
        ))
    return new_authors

class ScopusAffiliationData(BaseModel):
    afid: str
    name: str
    varients: List[str]
    city: str
    country: str
    doc_count: int


def test_scopus_get_institution_id():
    #http://api.elsevier.com:80/content/search/affiliation?start=0&count=5&query=affil(university)
    test_data = requests.get('https://dev.elsevier.com/payloads/search/affiliationSearchResp.json').text
    dict_struct = json.loads(test_data)
    results = dict_struct['search-results']['entry']
    new_results = []
    for result in results:
        identifier = result['dc:identifier']
        ident = identifier[identifier.find(':')+1:len(identifier)]
        affiliation_name = result['affiliation-name']
        affiliation_varients = [i['$'] for i in result['name-variant']]
        city = result['city']
        country = result['country']
        doc_count = result['document-count']
        #print(identifier)
        new_results.append(
            ScopusAffiliationData.parse_obj({
                'afid': ident,
                'name': affiliation_name,
                'varients': affiliation_varients,
                'city': city,
                'country': country,
                'doc_count': doc_count
            })
        )
    return new_results
