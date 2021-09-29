from postal.expand import expand_address
from postal.parser import parse_address
from typing import Optional, List, Tuple, Union
from pydantic import BaseModel
from matchmaker.query_engine.backends.pubmed_api import PubmedTopic, AbstractItem, IdSet

class ProcessedAuthorBase(BaseModel):
    institution: Optional[str]
    proc_institution: Optional[List[Tuple[str, str]]]

class ProcessedIndividual(ProcessedAuthorBase):
    last_name: str
    fore_name: str
    initials: str

class ProcessedCollective(ProcessedAuthorBase):
    collective_name:str


class ProcessedAuthor(BaseModel):
    __root__: Union[ProcessedIndividual, ProcessedCollective]


class ProcessedEFetchData(BaseModel):
    paper_id: IdSet
    title: str
    year: Optional[int]
    author_list: List[ProcessedAuthor]
    journal_title: str
    journal_title_abr: str
    keywords: Optional[List[str]]
    topics: List[PubmedTopic]
    abstract: Optional[Union[str, List[AbstractItem]]]

class ProcessedData(ProcessedEFetchData):
    references: Optional[List[ProcessedEFetchData]] = None
    cited_by: Optional[List[ProcessedEFetchData]] = None

ProcessedEFetchData.update_forward_refs()

def process_institution(institution):
    def remove_emails_from_phrase(initial_phrase):
        def find_all(a_str, sub):
            start = 0
            while True:
                start = a_str.find(sub, start)
                if start == -1: return
                yield start
                start += len(sub)
        
        def remove_from_phrase(phrase, to_remove):
            starts = [i[0] for i in to_remove]
            starts.sort()
            ends = [i[1] for i in to_remove]
            ends.sort()
            real_starts = [0] + ends
            real_ends = starts + [len(phrase)]
            if len(phrase) in real_starts:
                real_starts.remove(len(phrase))
                real_ends.remove(len(phrase))
            phrase_parts = []
            for counter, real_start in enumerate(real_starts):
                real_end = real_ends[counter]
                phrase_parts.append(phrase[real_start: real_end])
            new_phrase = ''.join(phrase_parts)
            return new_phrase
        
        words_to_remove = [
            'email',
            'electronic address'
        ]
        at_locations =list(find_all(initial_phrase, '@'))
        emails = []
        for at_location in at_locations:
            if at_location != -1:
                words = initial_phrase.split(' ')
                for word in words:
                    if '@' in word:
                        words_to_remove.append(word)
                        emails.append(word)
        
        to_remove = []
        for i in words_to_remove:
            start_phrase_loc = initial_phrase.lower().find(i)
            if start_phrase_loc != -1:
                end_phrase_loc = start_phrase_loc + len(i)
                to_remove.append((start_phrase_loc, end_phrase_loc))
        return remove_from_phrase(initial_phrase, to_remove), emails
    
    def parse_institution(new_institution):
        institution_split = new_institution.split(',')
        combined_sections = []
        for section in institution_split:
            expanded = expand_address(section)
            if expanded == []:
                to_parse = section
            else:
                to_parse = expanded[0]
            parsed_section = parse_address(to_parse)
            combined_sections = combined_sections + parsed_section

        return combined_sections
    
    new_institution, emails = remove_emails_from_phrase(institution)
    processed = parse_institution(new_institution)
    proc_emails = [(i, 'email') for i in emails]
    combined_proc = processed + proc_emails

    reduced_combined_proc = []
    for i in combined_proc:
        if i not in reduced_combined_proc:
            reduced_combined_proc.append(i)
    
    if reduced_combined_proc == []:
        reduced_combined_proc = None

    return reduced_combined_proc