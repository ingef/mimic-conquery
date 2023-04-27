import pandas as pd 
import json

icd_file =  "ICD10CM.csv"
json_file="ICD10CM.json"
df = pd.read_csv(icd_file,engine='python', names= ['category','digit','code','digit_description','description','category_name'])

def get_children_code(children_):
    list_children=[]
    for child in children_:
        list_children.append( df.code.loc[child])
    return list_children 

def get_children_index(df,category):
    return df.index[df['category']==category].tolist()

def get_parent_index(children):
    return children[0]

def remove_children(children):
    return children[1:]

parents=[]

categories=df['category'].unique()
for category in categories:
    children_index=get_children_index(df,category)
    parent_index=children_index[0]
    children_index=remove_children(children_index)
    parent={  
        "name" : df.code.loc[parent_index],
        "label" : df.code.loc[parent_index],
        "description" : df.description.loc[parent_index],
        "condition" : 
            {
            "type" : "EQUAL",
            "values" : get_children_code(children_index)
            },
        "children":[]
    }
    parents.append(parent)
        
    for child_index in children_index: 
        children= {
        "name" : df.code.loc[child_index],
        "label" : df.code.loc[child_index],
        "description": df.description.loc[child_index],
        "condition" : 
            {
            "type" : "EQUAL",
            "values" : [df.code.loc[child_index]]
            }
        }
        parent['children'].append(children)

json_object = json.dumps(parents, indent=4)
with open(json_file, "w") as outfile:
    outfile.write(json_object)

