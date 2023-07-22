# Odooless

![Build Status](https://github.com/Barameg/odooless/actions/workflows/build.yml/badge.svg)

An Odoo-like serverless ORM for AWS DynamoDB 


## Installation

``` pip install odooless ```


## Model Definition

To create a new model

``` python
from odooless import models


class Users(models.Model):
    _name = 'Users' # dynamodb table name
    _limit = 80 # define default limit number of records to get from db
    _fields = [
        {
            'name': 'fieldName',
            'type': 'S', # supported field types are Binary as B, Integer as N, String as S 
            'index': True, # create global secondary index for this attribute
        }, ... # attribute definition 
    ]
```

## Methods
Currently available methods
### create
``` python
    from models import Users

    someUser = Users().create({
        'key': 'value',
    }) # create single record

    someUsers = Users().create([
        {
            'key': 'value',
        },
        {
            'key': 'value',
        }, ...
    ]) # or create multiple records
```

### read
``` python
    from models import Users

    ids = [
        'UUID4',
        'UUID4',
        'UUID4',
    ]

    fields = [
        'field1',
        'field2',
        ....
    ]
    someUsers = Users().read(ids, fields) # returns recordset 
    for user in someUsers:
        print(user.name)
```

### search
``` python
    from models import Users

    domain = [
        ('field1', '=', 'value0'),
        ('field2', '>=', 'value1'),                                  
        ('field3', '<=', 'value2'),                                  
        ('field4', 'IN', ['value0', 'value1', 'value2',]),
        ('field5', 'between', ['value0', 'value1',]),
        ....
    ] # currently simple query operators soon will add full polish-notation support
    someUsers = users.search(field0=value, domain) # the search method takes index attribute name as a keyword parameter along with a domain that does not include this attribute and returns list of records

    for user in someUsers:
        print(user.name) 
```

### search_read
``` python
    from models import Users

    domain = [
        ('field1', '=', 'value0'),
        ('field2', '>=', 'value1'),
        ('field3', '<=', 'value2'),
        ('field4', 'IN', ['value0', 'value1', 'value2',]),
        ('field5', 'between', ['value0', 'value1',]),
        ....
    ] # currently simple query operators soon will add full polish-notation support

    fields = [
        'field1',
        'field2',
        ....
    ]
    someUsers = Users().search_read(field0=value, domain, fields) # the search method takes index attribute name as a keyword parameter along with a domain that does not include this attribute and returns list of records

    for user in someUsers:
        print(user.name) 
```
### write
``` python
    from models import Users

    users.write({
        'id': 'UUIDv4'
        'key': 'value',
    }) # you can update single record by passing its id to model method

    users.write([
        {
            'id': 'UUIDv4'
            'key': 'value',
        },
        {
            'id': 'UUIDv4'
            'key': 'value',
        },...
    ]) # you can update multiple records by passing id of record

    someUser = Users().read(ids)

    for user in someUsers:
        user.write({
            'key': 'value',
        }) # no need to include id if you use update on the instance
```



### delete
``` python
    from models import Users

    someUser = Users().delete(ids) # you can delete single or multiple records
```


