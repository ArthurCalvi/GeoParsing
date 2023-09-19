# GeoParsing
GeoParser for DataFrame to retrieve the smallest spatial entity. 

## Installation 
Dependencies : 

    pip install -r requirements.txt

NLP model :

    python -m spacy download xx_ent_wiki_sm

## Mechanisms to extract locations 
This algorithm combines NLP and Tree representation to extract the smallest spatial entity of a text. 

1. **Extracting interesting words with NLP** : Not all words are useful to locate the event. The entity recognition feature of spaCy multi-language model is used to extract locations, organizations or country/county/city-names. ![er](/images/er.png)
2. **Finding matches with OpenStreetMap (and GoogleMaps [optional])** :  an API is used to query the database. Then the results are organized into a tree structure to retrieve the smallest spatial entity. ![tree](/images/tree.png)
3. **Climbing the tree** to collect the spatial entity that satisfies some rules on the surface area. For instance, imposing a spatial entity between 100 and 1000 km2 returns the Los Angeles City spatial entity. ![im](/images/ex.png)

## How it works

Look at example.ipynb 
