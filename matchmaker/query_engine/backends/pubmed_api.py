import xmltodict
from urllib.parse import quote_plus
import xml.etree.ElementTree as xml_parse
from pydantic import BaseModel, Field
from typing import List, Union, Optional
import json

from matchmaker.query_engine.query_types import And, Or, Title, AuthorName, Journal, Abstract, Institution, Keyword, Year, StringPredicate
from typing import Annotated, Literal, Tuple, Dict
from aiohttp import ClientSession

def inspect_xml_dict(i):
    return xmltodict.parse(
        bytes(
            xml_parse.tostring(
                i, 
                encoding='utf8', 
                method='xml'
            )
        ).decode('unicode_escape')
    )
def inspect_xml(i):
    return json.dumps(
        inspect_xml_dict(i),
        indent=2
    )

#### E Search query def ####

and_int = And['PubmedESearchQuery']
or_int = Or['PubmedESearchQuery']

class Pmid(BaseModel):
    tag: Literal['pmid'] = 'pmid'
    operator: StringPredicate

class ELocationID(BaseModel):
    tag: Literal['elocationid'] = 'elocationid'
    operator: StringPredicate

class MeshTopic(BaseModel):
    tag: Literal['meshtopic'] = 'meshtopic'
    operator: StringPredicate

class PubmedESearchQuery(BaseModel):
    __root__: Annotated[  # type: ignore[misc]
    Union[
        and_int,  # type: ignore[misc]
        or_int,  # type: ignore[misc]
        Pmid,
        ELocationID,
        MeshTopic,
        Title,
        AuthorName,
        Journal,
        Abstract,
        Institution,
        Keyword,
        Year
    ],
    Field(discriminator='tag')]

and_int.update_forward_refs()
or_int.update_forward_refs()
PubmedESearchQuery.update_forward_refs()

#### End E Search query def ####

class PubmedESearchData(BaseModel):
    pubmed_id_list: List[str]
    count: int
    ret_max: int
    ret_start: int

# ESearch
async def esearch_on_query(
    query: PubmedESearchQuery,
    client: ClientSession,
    api_key: str = None
) -> PubmedESearchData:
    def query_to_term(query):
        def make_year_term(start_year:int = 1000, end_year:int = 3000):
            if start_year==end_year:
                return f'("{start_year}"[Date - Publication])'
            else:
                return f'("{start_year}"[Date - Publication] : "{end_year}"[Date - Publication])'

        def make_string_term(string, value, operator):
            if operator == 'in' and len(value) > 4:
                return f'({value}*[{string}])'
            elif operator == 'in':
                raise ValueError(f'Value {value} in section {string} too short for operator "in"')
            else:
                return f'({value}[{string}])'
        
        if query['tag'] == 'and':
            fields = query['fields_']
            return '('+' AND '.join([query_to_term(field) for field in fields])+')'
        elif query['tag'] == 'or':
            fields = query['fields_']
            return '('+' OR '.join([query_to_term(field) for field in fields])+')'
        elif query['tag'] == 'pmid':
            operator = query['operator']
            value = operator['value']
            return make_string_term('PMID', value, operator)
        elif query['tag'] == 'meshtopic':
            operator = query['operator']
            value = operator['value']
            return make_string_term('MeSH Major Topic', value, operator)
        elif query['tag'] == 'elocationid':
            operator = query['operator']
            value = operator['value']
            return make_string_term('Location ID', value, operator)
        elif query['tag'] == 'title':
            operator = query['operator']
            value = operator['value']
            return make_string_term('Title', value, operator)
        elif query['tag'] == 'author':
            operator = query['operator']
            value = operator['value']
            return make_string_term('Author', value, operator)
        elif query['tag'] == 'journal':
            operator = query['operator']
            value = operator['value']
            return make_string_term('Journal', value, operator)
        elif query['tag'] == 'abstract':
            operator = query['operator']
            value = operator['value']
            return make_string_term('Abstract', value, operator)
        elif query['tag'] == 'institution':
            operator = query['operator']
            value = operator['value']
            return make_string_term('Affiliation', value, operator)
        
        elif query['tag'] == 'keyword':
            operator = query['operator']
            value = operator['value']
            return make_string_term('Other Term', value, operator)
        
        elif query['tag'] == 'year':
            operator = query['operator']
            if operator['tag'] =='equal':
                value = operator['value']
                return make_year_term(value,value)
            elif operator['tag'] == 'lt':
                value = operator['value']
                return make_year_term(end_year=value)
            elif operator['tag'] == 'gt':
                value = operator['value']
                return make_year_term(start_year=value)
            elif operator['tag'] == 'range':
                lower_bound = operator['lower_bound']
                upper_bound = operator['upper_bound']
                return make_year_term(lower_bound,upper_bound)
            else:
                raise ValueError('Unknown tag')
        else:
            raise ValueError('Unknown tag')

    def make_search_given_term(
        term, 
        db='pubmed', 
        retmax:int = 10000, 
        prefix= 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/',
        api_key = None
    ):
        if api_key is None:
            return f'{prefix}esearch.fcgi?db={db}&retmax={retmax}&term={quote_plus(str(term))}'
        else:
            return f'{prefix}esearch.fcgi?db={db}&retmax={retmax}&term={quote_plus(str(term))}&api_key={api_key}'
    term = query_to_term(query.dict()['__root__'])
    search_url = make_search_given_term(term, api_key=api_key)

    output = await client.get(search_url)
    #print(output)
    print('search')
    raw_out = await output.text()
    proc_out = xml_parse.fromstring(raw_out)
    id_list = []
    for result in proc_out:
        if result.tag == 'IdList':
            id_list = id_list + [i.text for i in result.iterfind('Id')]
        elif result.tag == 'Count':
            count = result.text
        elif result.tag == 'RetMax':
            ret_max = result.text
        elif result.tag == 'RetStart':
            ret_start = result.text

    # Get metadata


    return PubmedESearchData(
        pubmed_id_list = id_list,
        count = count,
        ret_max = ret_max,
        ret_start = ret_start
    )

class PubmedELinkQuery(BaseModel):
    pubmed_id_list: List[str]
    linkname: str

class PubmedELinkData(BaseModel):
    id_mapper: Dict[str, Optional[List[str]]]

# Elink
async def elink_on_id_list(
    query: PubmedELinkQuery, 
    client: ClientSession,
    api_key = None
) -> PubmedELinkData:
    def make_elink_url(
            id_list,
            linkname,
            prefix= 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/',
            api_key = None,
        ):
            if api_key is None:
                return f'{prefix}elink.fcgi?dbfrom=pubmed&linkname={linkname}&id='+'&id='.join(id_list)
            else:
                return f'{prefix}elink.fcgi?dbfrom=pubmed&linkname={linkname}&api_key={api_key}&id='+'&id='.join(id_list)
    id_list = query.pubmed_id_list
    linkname = query.linkname
    url = make_elink_url(id_list, linkname, api_key = api_key)
    output = await client.get(url)
    #print(output)
    print('link')
    raw_references = await output.text()
    proc_ref = xmltodict.parse(raw_references)
    link_set = proc_ref['eLinkResult']['LinkSet']

    id_mapper = {}
    for link in link_set:
        id_value = link['IdList']['Id']
        if 'LinkSetDb' in link:
            link_set_db = link['LinkSetDb']['Link']
            link_proc = []
            if isinstance(link_set_db, list):
                link_proc = [i['Id'] for i in link_set_db]
            else:
                link_proc = [link_set_db['Id']]
            id_mapper[id_value] = link_proc
        else:
            id_mapper[id_value] = None
    return PubmedELinkData(id_mapper = id_mapper)





class PubmedEFetchQuery(BaseModel):
    pubmed_id_list: List[str]


#### E Fetch paper def ####
class PubmedTopic(BaseModel):
    descriptor: str
    qualifier: Optional[Union[str,List[str]]] = None

class PubmedAuthorBase(BaseModel):
    institution: Optional[str]
    #proc_institution: Optional[List[Tuple[str, str]]]

class PubmedIndividual(PubmedAuthorBase):
    last_name: str
    fore_name: Optional[str]
    initials: Optional[str]

class PubmedCollective(PubmedAuthorBase):
    collective_name:str


class PubmedAuthor(BaseModel):
    __root__: Union[PubmedIndividual, PubmedCollective]


class AbstractItem(BaseModel):
    label: Optional[str]
    nlm_category: Optional[str]
    text: Optional[str]

class IdSet(BaseModel):
    pubmed: str
    doi: Optional[str]
    pii: Optional[str]
    pmc: Optional[str]
    mid: Optional[str]

class PubmedEFetchData(BaseModel):
    paper_id: IdSet
    title: str
    year: Optional[int]
    author_list: List[PubmedAuthor]
    journal_title: str
    journal_title_abr: str
    keywords: Optional[List[str]]
    topics: List[PubmedTopic]
    abstract: Optional[Union[str, List[AbstractItem]]]




#### End E Fetch paper def ####

# EFetch
async def efetch_on_id_list(
    query: PubmedEFetchQuery,
    client: ClientSession,
    api_key: str = None
) -> List[PubmedEFetchData]:
    def make_fetch_given_ids(
        id_list,
        prefix= 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/',
        api_key: str = None
    ):
        #print(api_key)
        if api_key is None:
            return f'{prefix}efetch.fcgi?db=pubmed&retmode=xml&id={",".join(id_list)}'
        else:
            return f'{prefix}efetch.fcgi?db=pubmed&retmode=xml&api_key={api_key}&id={",".join(id_list)}'
    id_list = query.pubmed_id_list
    fetch_url = make_fetch_given_ids(id_list, api_key=api_key)
    #print(id_list)
    if len(id_list)>200:
        output = await client.post(make_fetch_given_ids([''], api_key=api_key), data = {'id': id_list})
    else:
        output = await client.get(fetch_url)
    print('fetch')
    #print(output)
    raw_fetch_out = await output.text()
    #print(raw_fetch_out)
    proc_out = xml_parse.fromstring(raw_fetch_out)
    papers = []
    for i in proc_out:

        medline_citation = i.find('MedlineCitation')
        if medline_citation is None:
            raise ValueError('Medline Citation not found')

        pubmed_data = i.find('PubmedData')
        if pubmed_data is None:
            raise ValueError('PubmedData not found')


        article_id_list = pubmed_data.find('ArticleIdList')
        if article_id_list is None:
            raise ValueError('ArticleIdList not found')
        
        articles = article_id_list.findall('ArticleId')
        ids_available= {i.attrib['IdType']: i.text for i in article_id_list}

        #pubmed_id = medline_citation.find('PMID').text
        article = medline_citation.find('Article')
        if article is None:
            raise ValueError('Article not found')
        keywordlist = medline_citation.find('KeywordList')
        if keywordlist is not None:
            keyword_text = [i.text for i in keywordlist.findall('Keyword')]
        else:
            keyword_text = None
        topics = []

        mesh_headings = medline_citation.find('MeshHeadingList')
        if mesh_headings is not None:
            mesh_heading_list = mesh_headings.findall('MeshHeading')
            for mesh_heading in mesh_heading_list:
                descriptor = mesh_heading.find('DescriptorName')
                if descriptor is None:
                    raise ValueError('DescriptorName not found')
                descriptor_text = descriptor.text
                qualifier = mesh_heading.find('QualifierName')
                if qualifier is not None:
                    if isinstance(qualifier, list):
                        new_qualifier = [j.text for j in qualifier]
                    else:
                        new_qualifier = qualifier.text
                else:
                    new_qualifier = None
                topics.append(
                    PubmedTopic(descriptor= descriptor_text,qualifier = new_qualifier)
                )
        journal = article.find('Journal')
        if journal is None:
            raise ValueError('Journal not found')
        journal_title_item = journal.find('Title')
        if journal_title_item is None:
            raise ValueError('Title not found')
        journal_title = journal_title_item.text
        journal_title_abr_item = journal.find('ISOAbbreviation')
        if journal_title_abr_item is None:
            raise ValueError('ISOAbbreviation not found')
        journal_title_abr = journal_title_abr_item.text
        year_pub_list = [i for i in journal.iter('Year')]
        if len(year_pub_list) == 1:
            year_pub = year_pub_list[0].text
        else:
            year_pub = None
        
        title_item = article.find('ArticleTitle')
        if title_item is None:
            raise ValueError('ArticleTitle not found')
        title = ' '.join(title_item.itertext())
        abstract = article.find('Abstract')
        if abstract is not None:
            abstract_text_list = abstract.findall('AbstractText')
            if abstract_text_list ==[]:
                new_abstract = None
            else:
                new_abstract = []
                for abstract_text in abstract_text_list:
                    if 'Label' in abstract_text.attrib:
                        label = abstract_text.attrib['Label']
                    else:
                        label = None
                    if 'NlmCategory' in abstract_text.attrib:
                        nlm_cat = abstract_text.attrib['NlmCategory']
                    else:
                        nlm_cat = None
                    text = abstract_text.text

                    item = AbstractItem(
                        label = label,
                        nlm_category = nlm_cat,
                        text = text
                    )
                    new_abstract.append(item)
        else:
            new_abstract = None

        author_list = article.iter("Author")
        author_list_proc = []
        for author in author_list:
            last_name_elem = author.find('LastName')
            affiliation_info = author.find("AffiliationInfo")
            if affiliation_info is not None:
                institution = affiliation_info.find('Affiliation').text
                #proc_institution = process_institution(institution)
            else:
                institution = None
                #proc_institution = None
            if last_name_elem is None:
                collective_item = author.find('CollectiveName')
                if collective_item is None:
                    raise ValueError('CollectiveName not found')
                collective = collective_item.text
                author_final = PubmedAuthor.parse_obj({
                    'collective_name': collective,
                    'institution': institution,
                    #'proc_institution': proc_institution
                })
            else:
                last_name = last_name_elem.text
                fore_name_item = author.find('ForeName')
                if fore_name_item is None:
                    fore_name = None
                else:
                    fore_name = fore_name_item.text
                initials_item = author.find('Initials')
                if initials_item is None:
                    initials = None
                else:
                    initials = initials_item.text
                author_final = PubmedAuthor.parse_obj({
                    'last_name': last_name, 
                    'fore_name': fore_name,
                    'initials': initials,
                    'institution': institution,
                    #'proc_institution': proc_institution
                })
            author_list_proc.append(author_final)            
            

        
        elocations = article.findall('ELocationID')
        if elocations is not None:
            elocation_dict = {i.attrib['EIdType']: i.text for i in elocations}
        else:
            elocation_dict = {}

        new_ids = {}
        for id_name,id_value in elocation_dict.items():
            if id_name not in ids_available:
                ids_available[id_name] = id_value

        pubmed_id = ids_available['pubmed']
        if 'doi' in ids_available:
            doi = ids_available['doi']
        else:
            doi = None
        if 'pii' in ids_available:
            pii = ids_available['pii']
        else:
            pii = None
        if 'pmc' in ids_available:
            pmc = ids_available['pmc']
        else:
            pmc = None
        if 'mid' in ids_available:
            mid = ids_available['mid']
        else:
            mid = None
        
        id_set = IdSet(
            pubmed = pubmed_id,
            doi = doi,
            pii = pii,
            pmc = pmc,
            mid = mid
        )

        paper_data = PubmedEFetchData(
            paper_id = id_set,
            title = title, 
            year = year_pub,
            author_list = author_list_proc,
            journal_title = journal_title,
            journal_title_abr = journal_title_abr,
            institution = institution,
            keywords = keyword_text,
            topics = topics,
            abstract = new_abstract
        )
        papers.append(paper_data)
    return papers
