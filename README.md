# Welcome to Matchmaker!

Matchmaker is a tool for identifying potential research collaborators on an individual level for research projects between two institutions.  The typical use case is between two known universities who have a formal research partnership in place, but are yet to have their researchers collaborating.

The tool is intended to be advisory.  It returns name pairings in order of match quality, and potentially any easily found public contact details.  Matches and their quality are determined and graded by a Matchmaking Engine.

By making appropriate queries to a set of Query Engines, this Matchmaking Engine can cyclically gather data from several bibliographical databases.  This use of data by the Matchmaking algorithm and its outputs reflects the project’s core question: “can high quality collaborative research opportunities be feasibly identified via bibliographic data?”

# Motivation

Traditionally academic collaborations are investigator-led “bottom up” interactions arising because one researcher directly contacts another based on reading the latter’s published work or through chance encounters at conferences or through introductions by mutual acquaintances. 

The newer, institution-led “top down” model is where leaders at two institutions identify the other as worthy institutional partners, and then sign an agreement or Memorandum of Understanding (MoU) to “promote collaboration”. Sometimes the institutions have pre-existing researcher-led collaborations but more often, these are few or non-existent and there is no clear mechanism for turning the MoU into actual research collaborations. 


# Installation

You'll need libpostal to install matchmaker - instructions on how to do this can be found [here](https://github.com/openvenues/libpostal#installation-maclinux]).

You'll also need poetry - instructions can be found [here](https://python-poetry.org/docs/#installation).


Next, in the base directory run:

`poetry install`

Now, you need to make a secret file that contains your api keys and institution token:

In the root of the repo:

`nano secret.py`

And place inside it:
```py
pubmed_api_key = 'some_string'
scopus_api_key = 'some_string'
scopus_inst_token = 'some_string'
```

# Usage

To run the full example:

`cd ./examples`

`poetry run python3 full_backend_test.py`