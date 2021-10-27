from pydantic import BaseModel
from typing import List, Union, Literal, Optional, Any

from matchmaker.query_engine.query_types import PaperSearchQuery, \
        AuthorSearchQuery
from matchmaker.query_engine.data_types import PaperData, AuthorData
from matchmaker.query_engine.slightly_less_abstract import SlightlyLessAbstractQueryEngine
from matchmaker.query_engine.backend import Backend

from urllib.parse import quote_plus
import xml.etree.ElementTree as xml_parse
import requests # type: ignore
import json
from enum import Enum

def extract_id(identifier):
    return identifier[identifier.find(':')+1:len(identifier)]


class ScopusAffiliationQuery(BaseModel):
    afid: str
    affil: str

class ScopusAffiliationData(BaseModel):
    afid: str
    name: str
    city: Optional[str]
    country: Optional[str]
    doc_count: Optional[int] = None
    variants: Optional[List[str]] = None

def test_scopus_get_institutions():
    #http://api.elsevier.com:80/content/search/affiliation?start=0&count=5&query=affil(university)
    test_data = requests.get('https://dev.elsevier.com/payloads/search/affiliationSearchResp.json').text
    dict_struct = json.loads(test_data)
    results = dict_struct['search-results']['entry']
    new_results = []
    for result in results:
        identifier = result['dc:identifier']
        ident = extract_id(identifier)
        affiliation_name = result['affiliation-name']
        affiliation_variants = [i['$'] for i in result['name-variant']]
        city = result['city']
        country = result['country']
        doc_count = result['document-count']
        new_results.append(
            ScopusAffiliationData.parse_obj({
                'afid': ident,
                'name': affiliation_name,
                'variants': affiliation_variants,
                'city': city,
                'country': country,
                'doc_count': doc_count
            })
        )
    return new_results




class SubjectArea(Enum):
    agriculture = 'AGRI'
    arts = 'ARTS'
    biochemistry = 'BIOC'
    business = 'BUSI'
    chem_engineering = 'CENG'
    chemistry = 'CHEM'
    computer_sci = 'COMP'
    decision_sci = 'DECI'
    dentistry = 'DENT'
    earth_and_planetary = 'EART'
    economics = 'ECON'
    energy = 'ENER'
    engineering = 'ENGI'
    environmental_sci = 'ENVI'
    health_professions = 'HEAL'
    immunology = 'IMMU'
    materials = 'MATE'
    mathematics = 'MATH'
    medicine = 'MEDI'
    neuroscience = 'NEUR'
    nursing = 'NURS'
    pharmacology = 'PHAR'
    physics = 'PHYS'
    psychology = 'PSYC'
    social_sciences = 'SOCI'
    veterinary = 'VETE'
    multidisciplinary = 'MULT'

class ScopusAuthorQuery(BaseModel):
    affiliation_id: str
    affiliation: str
    author_id: str
    subject_area: SubjectArea


class Subject(BaseModel):
    name: str
    frequency: str
    abbr: str

class Name(BaseModel):
    surname: str
    initials: Optional[str] = None
    given_name: Optional[str] = None

class ScopusAuthorData(BaseModel):
    auth_id: str
    preferred_name: Name
    variants: List[Name]
    doc_count: int
    subjects: List[Subject]
    current_affiliation: ScopusAffiliationData

def test_scopus_get_authors():
    test_data = requests.get('https://dev.elsevier.com/payloads/search/authorSearchResp.json').text
    dict_struct = json.loads(test_data)
    results = dict_struct['search-results']['entry']
    new_results = []
    for result in results:
        identifier = extract_id(result['dc:identifier'])
        preferred_name = result['preferred-name']
        proc_pref_name = Name.parse_obj(preferred_name)

        variants = result['name-variant']
        proc_variants = []
        for variant in variants:
            proc_variants.append(Name.parse_obj(variant))
        
        doc_count = result['document-count']

        new_subjects = []
        subjects = result['subject']
        for subject in subjects:
            freq = subject['@frequency']
            abbr = subject['@abbr']
            name = subject['$']
            new_subjects.append(
                Subject(
                    name = name,
                    frequency = freq,
                    abbr = abbr
                )
            )
        affil_current = result['affiliation-current']
        afid = affil_current['affiliation-id']
        affil_name = affil_current['affiliation-name']
        affil_city = affil_current['affiliation-city']
        affil_country = affil_current['affiliation-country']
        new_affil_current = ScopusAffiliationData(
            afid = afid,
            name = affil_name,
            city = affil_city,
            country = affil_country
        )
        new_results.append(
            ScopusAuthorData.parse_obj({
                'auth_id': identifier,
                'preferred_name': proc_pref_name,
                'variants': proc_variants,
                'doc_count': doc_count,
                'subjects': new_subjects,
                'current_affiliation': new_affil_current
            })
        )

    return new_results


#https://dev.elsevier.com/sc_search_tips.html
class ScopusPaperQuery(BaseModel):
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
    class Author(BaseModel):
        authid: str
        authname: str
        surname: str
        initials: str
        given_name: Optional[str] = None
    doi: Optional[str]
    title: str
    creator: str
    scopus_id: str
    publication: str
    cover_date: str
    cover_display_date: str
    authors: List[Author]
    description: str
    affiliations: List[ScopusAffiliationData]
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
        else:
            doi = None
        description = result['dc:description']

        proc_affiliations = []
        affiliations = result['affiliation']
        for affiliation in affiliations:
            afid = affiliation['afid']
            affiliation_name = affiliation['affilname']
            affiliation_variants = [i['$'] for i in affiliation['name-variant']]
            affiliation_city = affiliation['affiliation-city']
            affiliation_country = affiliation['affiliation-country']
            proc_affiliations.append({
                'afid': afid,
                'name': affiliation_name,
                'variants': affiliation_variants,
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
        new_results.append(ScopusPaperData.parse_obj({
            'title': title,
            'creator': creator,
            'scopus_id': scopus_id,
            'publication': publication,
            'cover_date': cover_date,
            'cover_display_date': cover_display_date,
            'doi': doi,
            'authors': proc_authors,
            'description': description,
            'affiliations': proc_affiliations
        }))
    return new_results

