from pydantic import BaseModel, root_validator
from typing import Optional

# Datatype invarient: Every field of this model uniquely identifies a paper
class PaperID(BaseModel):
    doi: Optional[str] = None
    pubmed_id: Optional[str] = None
    scopus_id: Optional[str] = None
    @root_validator(allow_reuse=True)
    def one_or_more_selected(cls, values):
        selected_ids = []
        for id_name, id_value in values.items():
            if id_value is not None:
                selected_ids.append(id_value)
        if len(selected_ids)==0:
            raise ValueError('No ids selected')
        return values