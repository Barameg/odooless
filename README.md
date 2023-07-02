# Odooless

An Odoo-like serverless ORM for AWS DynamoDB 


## Model

To create a new model

``` python
from models import Model


class Users(Model):
    _name = 'Users'
    _limit = 80 # define limit number of records to get from db
    _fields = [
        {
            'name': 'fieldName',
            'type': 'S', # supported field types are Binary as B, Integer as N, String as S 
            'index': True, 
        }, ...
    ]
```

## Methods
Currently available methods
### create
``` python
    from models import users

    someUser = users.create({
        'key': 'value',
    }) # create single record

    someUsers = users.create([
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
    from models import users

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
    someUsers = users.read(ids, fields) # returns recordset 
    for user in someUsers:
        print(user.name)
```

### search
``` python
    from models import users

    domain = [
        ('field', '=', 'value'),
        ....
    ] # currently simple query operators soon will add full polish-notation support
    fields = [
        'field1',
        'field2',
        ....
    ]
    someUsers = users.search(domain) # returns list of records

    for user in someUsers:
        print(user.name) 
```

### search_read
``` python
    from models import users

    domain = [
        ('field', '=', 'value'),
        ....
    ] # currently simple query operators soon will add full polish-notation support
    fields = [
        'field1',
        'field2',
        ....
    ]
    someUsers = users.search(domain) # returns list of dictionaries

    for user in someUsers:
        print(user.name) 
```
### write
``` python
    from models import users

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

    someUser = users.read(ids)

    for user in someUsers:
        user.write({
            'key': 'value',
        }) # no need to include id if you use update on the instance
```



### delete
``` python
    from models import users

    someUser = users.delete(ids) # you can delete single or multiple records
```


