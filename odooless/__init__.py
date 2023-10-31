import boto3
import os
import uuid
import time
import copy


class Database:
    _service_name = "dynamodb"
    _endpoint_url = None
    _region_name = None
    _aws_access_key_id = None
    _aws_secret_access_key = None
    _session = None
    _client = None
    _resource = None

    def __init__(self):
        pass

    def connect(self):
        self._session = boto3.Session(
            aws_access_key_id=self._aws_access_key_id,
            aws_secret_access_key=self._aws_secret_access_key,
            region_name=self._region_name,
        )
                
        self._client = self._session.client(
            service_name=self._service_name,
            endpoint_url=self._endpoint_url,
            region_name=self._region_name,
            aws_access_key_id=self._aws_access_key_id,
            aws_secret_access_key=self._aws_secret_access_key

        )
        self._resource = self._session.resource(
            service_name=self._service_name,
            endpoint_url=self._endpoint_url,
            region_name=self._region_name,
            aws_access_key_id=self._aws_access_key_id,
            aws_secret_access_key=self._aws_secret_access_key
        )
        return self


DB = Database()

class Record:
    _data = {}
    def __init__(self, data):
        self._data = data

    def __iter__(self):
        return iter(self._data.items())

    def __getattr__(self, name):
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"'Record' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        if name in self._data:
            self._data[name] = value
        else:
            super().__setattr__(name, value)

    def __str__(self):
        return f'{self._data}'


    @classmethod
    def _set_attribute(cls, name, value):
        cls._data[name] = value

class RecordSet:
    _model = None

    def __init__(self, model):
        self._model = model

    def __iter__(self):
        return iter(self._model._records)

    def __len__(self):
        return len(self._model._records)

    def __getitem__(self, index):
        return self._model._records[index]

    def __str__(self):
        ids = ''
        for rec in self._model._records:
            ids += f'{rec.id}, '
        return f"<RecordSet {self._model._name}({ids})>"
   
    def create(self, records):
        return self._model._create(records)

    def read(self, id, fields):
        return self._model._read(id, fields)

    def update(self, records):
        return self._model.update(records)

    def search(self, domain=[], fields=[], offset=None, limit=None, sort='asc', **kwargs):
        return self._model._search(domain=domain, fields=fields, offset=offset, limit=limit, sort=sort, **kwargs)

    def search_count(self, domain=[], **kwargs):
        result = self._model._search(domain=domain, fields=['id'], **kwargs)
        return len(result)

    def delete(self, ids=[]):
        return self._model._delete(ids)

class Field:
    _name = None
    _default = False
    _hidden = False
    _string = None
    _type = 'S' # types available for DynamoDB are B, N, S
    _index = False
    
    def __init__(self, name, default=False, hidden=False, string=None, type='S', index=False):
        self._name = name
        self._default = default
        self._hidden = hidden
        self._string = string
        self._type = type
        self._index = index

DEFAULT_FIELDS = [
    Field('id', index=True, hidden=False, string='ID'),
    Field('createdAt', index=True, hidden=False, string='Created At'),
    Field('updatedAt', index=True, hidden=False, string='Updated At'),
    Field('modelName', index=True, hidden=True, string='Model')
]


class Model:
    _name = None
    _table = None
    _fields = []
    _limit = 80
    _attribute_definitions = None
    _global_secondary_indexes = None
    _billing_mode = 'PAY_PER_REQUEST'
    _db = None
    _records = None
    _LastEvaluatedKey = None
    _id = None
    _values = {}

    def __init__(self):
        self._init()

    def __iter__(self):
        return iter(self._records)

    def __len__(self):
        return len(self._records)

    def __getitem__(self, index):
        return self._records[index]

    def __str__(self):
        ids = ''
        for rec in self._records:
            ids += f'{rec.get("id")}, '
        return f"<RecordSet {self._name}({ids})>"

    @classmethod
    def _init(cls):
        try:
            cls._db = DB.connect()
        except Exception as e:
            raise Exception(f'Could not connect to cloud')
        try:
            cls._table = cls._db._resource.Table(cls._name)
            cls._attribute_definitions = cls._table.attribute_definitions
            cls._global_indexes = cls._table.global_secondary_indexes
        except Exception as e:
            cls._table = cls._create_table()

    @classmethod
    def _create_table(
        cls,
    ):
        create_params = {
            'TableName':cls._name,
            'BillingMode':cls._billing_mode,
        }
        KeySchema = []
        AttributeDefinitions = []
        GlobalSecondaryIndexes = []

        for field in DEFAULT_FIELDS:
            if field._name == 'id':
                KeySchema.append({
                    'AttributeName': field._name,
                    'KeyType': 'HASH'
                })

            AttributeDefinitions.append({
                'AttributeName': field._name,
                'AttributeType': field._type
            })
            GlobalSecondaryIndexes.append({
                'IndexName': f'{field._name}Index',
                'KeySchema': [
                    {
                        'AttributeName': field._name,
                        'KeyType': 'HASH'
                    },
                ],
                'Projection': {
                    'ProjectionType': 'ALL',
                },
            })


        for field in cls._fields:
            if field._index:
                AttributeDefinitions.append({
                    'AttributeName': field._name,
                    'AttributeType': field._type if field._type and field._type in [
                        'B', 'N'
                    ] else 'S'
                })
                GlobalSecondaryIndexes.append({
                    'IndexName': f'{field._name}Index',
                    'KeySchema': [
                        {
                            'AttributeName': field._name,
                            'KeyType': 'HASH'
                        },
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL',
                    },
                })
        create_params['KeySchema'] = KeySchema
        create_params['AttributeDefinitions'] = AttributeDefinitions
        create_params['GlobalSecondaryIndexes'] = GlobalSecondaryIndexes
        try:
            cls._table = cls._db._resource.create_table(
                **create_params
            )
            cls._table.wait_until_exists()
        except Exception as e:
            raise Exception(e)
        return cls._table

    @classmethod
    def _create(cls, records):
        cls._table = cls._db._resource.Table(cls._name)
        cls._records = []
        required_fields = list(filter(lambda field: field._required, cls._fields))
        existingFields = list(map(lambda field: field._name, cls._fields))
        if isinstance(records, list):
            # check required fields
            for record in records:
                for required_field in required_fields:
                    if required_field._name not in record:
                        raise Exception(f'Missing required field: {required_field._name}')
            # check non existing and default fields
            for record in records:
                for key, val in record.items():
                    if key in DEFAULT_FIELDS:
                        raise Exception(f'Default field {key} can not be used')
                    
                    if key not in existingFields and key not in DEFAULT_FIELDS:
                        raise Exception(f'Invalid field: {key}')
            try:
                with cls._table.batch_writer() as batch:
                    for record in records:                    
                        record['id'] = str(uuid.uuid4())
                        record['createdAt'] = str(int(time.time()))
                        record['updatedAt'] = str(int(time.time()))
                        record['modelName'] = cls._name
                        batch.put_item(Item=record)
                        record = Record(record)
                        cls._records.append(record)
            except Exception as e:
                raise Exception(e)
            return RecordSet(cls)
        if isinstance(records, dict):
            record = records
            # check required fields
            for required_field in required_fields:
                if required_field._name not in record:
                    raise Exception(f'Missing required field: {required_field._name}')
            
            # check non existing and default fields
            for key, val in record.items():
                if key in DEFAULT_FIELDS:
                    raise Exception(f'Default field {key} can not be used')
                
                if key not in existingFields and key not in DEFAULT_FIELDS:
                    raise Exception(f'Invalid field: {key}')

            try:
                record['id'] = str(uuid.uuid4())
                record['createdAt'] = str(int(time.time()))
                record['updatedAt'] = str(int(time.time()))
                record['modelName'] = cls._name
                cls._table.put_item(Item=record)
                record = Record(record)
                cls._records.append(record)
            except Exception as e:
                raise Exception(e)
            return RecordSet(cls)
        raise ValueError()
    
    def create(self, records):
        return self._create(records)

    @classmethod
    def _read(cls, id, fields=[]):
        records = cls._search(id=id, fields=fields)
        if records:
            return records[0]
        return False

    def read(self, id, fields=[]):
        return self._read(id, fields)

    @classmethod
    def filter_expression_from_domain(cls, domain):
        FilterExpression = ''
        ExpressionAttributeNames = {}
        ExpressionAttributeValues = {}
        if not isinstance(domain, list):
            raise Exception(f'Domain mult be a list')
        for key, expression in enumerate(domain):
            if not isinstance(expression, list) and not isinstance(expression, tuple) and expression.upper() not in ['&', '|', 'AND', 'OR']:
                raise Exception(f'Domain expressions must be either list or tuple')
            
            if key == 0 and not isinstance(expression, list) and not isinstance(expression, tuple):
                raise Exception(f'First Expression must be either list or tuple')
            if key < len(domain) - 1:
                if isinstance(expression, list) or isinstance(expression, tuple):
                    attribute = expression[0]
                    operator = expression[1]
                    attribute_value = expression[2]
                    # Negating Condition Expression
                    if '!' in operator:
                        operator = operator.replace('!', '')
                        FilterExpression += f"NOT ("
                        
                        if operator in ['=', '<>', '<', '<=', '>', '>=']:
                            ExpressionAttributeValues[f':{attribute}{key}'] = attribute_value
                            ExpressionAttributeNames[f'#{attribute}{key}'] = attribute
                            FilterExpression += f"#{attribute}{key} {operator} :{attribute}{key}) "
                        
                        if operator.upper() == 'IN':
                            if isinstance(attribute_value, list):
                                operand = f''
                                for k, v in enumerate(attribute_value):
                                    if k < len(attribute_value) - 1:
                                        operand += f':{attribute}{key}{k}, '
                                    else:
                                        operand += f':{attribute}{key}{k}'
                                    ExpressionAttributeValues[f':{attribute}{key}{k}'] = v
                                operand = f'({operand})'
                                FilterExpression += f"#{attribute}{key} {operator.upper()} {operand}) "
                                ExpressionAttributeNames[f'#{attribute}{key}'] = f'{attribute}'
                            else:
                                raise Exception(f"{attribute} value must be a list, you passed {attribute_value}")
                        if operator.upper() == 'BETWEEN':
                            if isinstance(attribute_value, list) and len(attribute_value) == 2:
                                operand = f''
                                for k, v in enumerate(attribute_value):
                                    if k < len(attribute_value) - 1:
                                        operand += f':{attribute}{key}{k} And '
                                    else:
                                        operand += f':{attribute}{key}{k}'
                                    ExpressionAttributeValues[f':{attribute}{key}{k}'] = v
                                FilterExpression += f'#{attribute}{key} {operator.upper()} {operand}) '
                            else:
                                raise Exception(f"{attribute} value must be a list with length of 2, you passed {attribute_value}")
                            ExpressionAttributeNames[f'#{attribute}{key}'] = f'{attribute}'
                            ExpressionAttributeValues[f':{attribute}{key}'] = f'{operand}'
                        if operator.upper() == 'BEGINS_WITH':
                            FilterExpression += f'begins_with(#{attribute}{key}, :{attribute}{key})) '
                            ExpressionAttributeNames[f'#{attribute}{key}'] = f'{attribute}'
                            ExpressionAttributeValues[f':{attribute}{key}'] = f'{attribute}'
                        if operator.upper() == 'CONTAINS':
                            FilterExpression += f'contains(#{attribute}{key}, :{attribute}{key})) '
                            ExpressionAttributeNames[f'#{attribute}{key}'] = f'{attribute}'
                            ExpressionAttributeValues[f':{attribute}{key}'] = f'{attribute}'                        
                    else:
                        if operator in ['=', '<>', '<', '<=', '>', '>=']:
                            ExpressionAttributeValues[f':{attribute}{key}'] = attribute_value
                            ExpressionAttributeNames[f'#{attribute}{key}'] = attribute
                            FilterExpression += f"#{attribute}{key} {operator} :{attribute}{key} "
                        if operator.upper() == 'IN':
                            # #ec581 IN (:ec581, :ec582)
                            if isinstance(attribute_value, list):
                                operand = f''
                                for k, v in enumerate(attribute_value):
                                    if k < len(attribute_value) - 1:
                                        operand += f':{attribute}{key}{k}, '
                                    else:
                                        operand += f':{attribute}{key}{k}'
                                    ExpressionAttributeValues[f':{attribute}{key}{k}'] = v
                                operand = f'({operand})'
                                FilterExpression += f"#{attribute}{key} {operator.upper()} {operand} "
                                ExpressionAttributeNames[f'#{attribute}{key}'] = f'{attribute}'
                            else:
                                raise Exception(f"{attribute} value must be a list, you passed {attribute_value}")
                        if operator.upper() == 'BETWEEN':
                            # #ec584 BETWEEN :ec584 AND :ec585
                            if isinstance(attribute_value, list) and len(attribute_value) == 2:
                                operand = f''
                                for k, v in enumerate(attribute_value):
                                    if k < len(attribute_value) - 1:
                                        operand += f':{attribute}{key}{k} And '
                                    else:
                                        operand += f':{attribute}{key}{k}'
                                    ExpressionAttributeValues[f':{attribute}{key}{k}'] = v
                                FilterExpression += f'#{attribute}{key} {operator.upper()}  {operand} '
                            else:
                                raise Exception(f"{attribute} value must be a list with length of 2, you passed {attribute_value}")
                            ExpressionAttributeNames[f'#{attribute}{key}'] = f'{attribute}'
                            ExpressionAttributeValues[f':{attribute}{key}'] = f'{operand}'
                        if operator.upper() == 'BEGINS_WITH':
                            FilterExpression += f'begins_with(#{attribute}{key}, :{attribute}{key}) '
                            ExpressionAttributeNames[f'#{attribute}{key}'] = f'{attribute}'
                            ExpressionAttributeValues[f':{attribute}{key}'] = f'{attribute_value}'
                        if operator.upper() == 'CONTAINS':
                            FilterExpression += f'contains(#{attribute}{key}, :{attribute}{key}) '
                            ExpressionAttributeNames[f'#{attribute}{key}'] = f'{attribute}'
                            ExpressionAttributeValues[f':{attribute}{key}'] = f'{attribute_value}'
                else:
                    # handle condition AND OR
                    FilterExpression += f"{expression.upper().replace('|', 'Or').replace('&', 'And')} "
            
            # final condition expression
            else:
                if isinstance(expression, list) or isinstance(expression, tuple):
                    attribute = expression[0]
                    operator = expression[1]
                    attribute_value = expression[2]

                    # Negating Condition Expression
                    if '!' in operator:
                        operator = operator.replace('!', '')
                        FilterExpression += f"NOT ("
                        
                        if operator in ['=', '<>', '<', '<=', '>', '>=']:
                            ExpressionAttributeValues[f':{attribute}{key}'] = attribute_value
                            ExpressionAttributeNames[f'#{attribute}{key}'] = attribute
                            FilterExpression += f"#{attribute}{key} {operator} :{attribute}{key})"
                        
                        if operator.upper() == 'IN':
                            if isinstance(attribute_value, list):
                                operand = f''
                                for k, v in enumerate(attribute_value):
                                    if k < len(attribute_value) - 1:
                                        operand += f':{attribute}{key}{k}, '
                                    else:
                                        operand += f':{attribute}{key}{k}'
                                    ExpressionAttributeValues[f':{attribute}{key}{k}'] = v
                                operand = f'({operand})'
                                FilterExpression += f"#{attribute}{key} {operator.upper()} {operand})"
                                ExpressionAttributeNames[f'#{attribute}{key}'] = f'{attribute}'
                            else:
                                raise Exception(f"{attribute} value must be a list, you passed {attribute_value}")
                        if operator.upper() == 'BETWEEN':
                            if isinstance(attribute_value, list) and len(attribute_value) == 2:
                                operand = f''
                                for k, v in enumerate(attribute_value):
                                    if k < len(attribute_value) - 1:
                                        operand += f':{attribute}{key}{k} And '
                                    else:
                                        operand += f':{attribute}{key}{k}'
                                    ExpressionAttributeValues[f':{attribute}{key}{k}'] = v
                                FilterExpression += f'#{attribute}{key} {operator.upper()} {operand}) '
                            else:
                                raise Exception(f"{attribute} value must be a list with length of 2, you passed {attribute_value}")
                            ExpressionAttributeNames[f'#{attribute}{key}'] = f'{attribute}'
                            ExpressionAttributeValues[f':{attribute}{key}'] = f'{operand}'
                        if operator.upper() == 'BEGINS_WITH':
                            FilterExpression += f'begins_with(#{attribute}{key}, :{attribute}{key}))'
                            ExpressionAttributeNames[f'#{attribute}{key}'] = f'{attribute}'
                            ExpressionAttributeValues[f':{attribute}{key}'] = f'{attribute_value}'
                        if operator.upper() == 'CONTAINS':
                            FilterExpression += f'contains(#{attribute}{key}, :{attribute}{key}))'
                            ExpressionAttributeNames[f'#{attribute}{key}'] = f'{attribute}'
                            ExpressionAttributeValues[f':{attribute}{key}'] = f'{attribute_value}'                        
                    else:
                        if operator in ['=', '<>', '<', '<=', '>', '>=']:
                            ExpressionAttributeValues[f':{attribute}{key}'] = attribute_value
                            ExpressionAttributeNames[f'#{attribute}{key}'] = attribute
                            FilterExpression += f"#{attribute}{key} {operator} :{attribute}{key}"
                        if operator.upper() == 'IN':
                            # #ec581 IN (:ec581, :ec582)
                            if isinstance(attribute_value, list):
                                operand = f''
                                for k, v in enumerate(attribute_value):
                                    if k < len(attribute_value) - 1:
                                        operand += f':{attribute}{key}{k}, '
                                    else:
                                        operand += f':{attribute}{key}{k}'
                                    ExpressionAttributeValues[f':{attribute}{key}{k}'] = v
                                operand = f'({operand})'
                                FilterExpression += f"#{attribute}{key} {operator.upper()} {operand}"
                                ExpressionAttributeNames[f'#{attribute}{key}'] = f'{attribute}'
                            else:
                                raise Exception(f"{attribute} value must be a list, you passed {attribute_value}")
                        if operator.upper() == 'BETWEEN':
                            # #ec584 BETWEEN :ec584 AND :ec585
                            if isinstance(attribute_value, list) and len(attribute_value) == 2:
                                operand = f''
                                for k, v in enumerate(attribute_value):
                                    if k < len(attribute_value) - 1:
                                        operand += f':{attribute}{key}{k} And '
                                    else:
                                        operand += f':{attribute}{key}{k}'
                                    ExpressionAttributeValues[f':{attribute}{key}{k}'] = v
                                FilterExpression += f'#{attribute}{key} {operator.upper()}  {operand}'
                            else:
                                raise Exception(f"{attribute} value must be a list with length of 2, you passed {attribute_value}")
                            ExpressionAttributeNames[f'#{attribute}{key}'] = f'{attribute}'
                            ExpressionAttributeValues[f':{attribute}{key}'] = f'{operand}'
                        if operator.upper() == 'BEGINS_WITH':
                            FilterExpression += f'begins_with(#{attribute}{key}, :{attribute}{key})'
                            ExpressionAttributeNames[f'#{attribute}{key}'] = f'{attribute}'
                            ExpressionAttributeValues[f':{attribute}{key}'] = f'{attribute_value}'
                        if operator.upper() == 'CONTAINS':
                            FilterExpression += f'contains(#{attribute}{key}, :{attribute}{key})'
                            ExpressionAttributeNames[f'#{attribute}{key}'] = f'{attribute}'
                            ExpressionAttributeValues[f':{attribute}{key}'] = f'{attribute_value}'                   
                else:
                    raise Exception(f'Final expression must be either list or tuple')
        return FilterExpression, ExpressionAttributeNames, ExpressionAttributeValues

    @classmethod
    def _search(cls, domain=[], fields=[], offset=None, limit=None, sort='asc', **kwargs):
        params = {}
        response = []
        if domain:
            FilterExpression, ExpressionAttributeNames, ExpressionAttributeValues = cls.filter_expression_from_domain(domain)
            params['FilterExpression'] = FilterExpression
            params['ExpressionAttributeNames'] = ExpressionAttributeNames
            params['ExpressionAttributeValues'] = ExpressionAttributeValues

        if fields:
            ProjectionExpression = ''
            if 'id' not in fields:
                ProjectionExpression += 'id, '
            for key, field in enumerate(fields):
                model_fields = list(map(lambda f: f.get('name'), cls._fields))
                if field not in model_fields and field not in DEFAULT_FIELDS:
                    raise Exception(f'Field {field} does not exist')
                if key < len(fields)-1:
                    ProjectionExpression += f'{field},'
                else:
                    ProjectionExpression += f'{field}'
            params['ProjectionExpression'] = ProjectionExpression

        if limit:
            params['Limit'] = limit if limit else cls._limit

        if offset:
            params['ExclusiveStartKey'] = {
                'id': offset
            }
        
        if not kwargs:
            kwargs['modelName'] = cls._name

        first_key = next(iter(kwargs))
        IndexName = f'{first_key}Index'
        KeyConditionExpression = f'#{first_key} = :{first_key}'
        params['IndexName'] = IndexName
        params['KeyConditionExpression'] = KeyConditionExpression
        if 'ExpressionAttributeNames' in params and 'ExpressionAttributeValues' in params:
            params['ExpressionAttributeNames'][f'#{first_key}'] = f'{first_key}'
            params['ExpressionAttributeValues'][f':{first_key}'] = kwargs[first_key]
        else:
            params['ExpressionAttributeNames'] = {}
            params['ExpressionAttributeNames'][f'#{first_key}'] = f'{first_key}'

            params['ExpressionAttributeValues'] = {}
            params['ExpressionAttributeValues'][f':{first_key}'] = kwargs[first_key]
        
        if sort.lower() == 'desc':
            params['ScanIndexForward'] = False
        try:
            response = cls._table.query(**params)
        except Exception as e:
            raise Exception(f'{e}')
        cls._records = []
        for item in response['Items']:
            item = Record(item)
            cls._records.append(item)
        return RecordSet(cls)

    
    def search(self, domain=[], fields=[], offset=None, limit=None, sort='asc', **kwargs):
        return self._search(domain=domain, fields=fields, offset=offset, limit=limit, sort=sort, **kwargs)

    def search_count(self, domain=[], **kwargs):
        result = self.search(domain=domain, fields=['id'], **kwargs)
        return len(result)
    
    def update(self, records):
        if isinstance(records, list):
            return self._update(records)
        if isinstance(records, dict):
            return self._update(records)
        return

    @classmethod
    def _write_single_record(cls, values):
        try:
            with cls._table.batch_writer() as batch:
                record = cls._read(values.get('id'))
                for key, value in values.items():
                    if key not in DEFAULT_FIELDS \
                            and key not in list(map(
                        lambda field: field._name, cls._fields)
                    ):
                        raise Exception(f'{key} does not exist')
                    if key not in DEFAULT_FIELDS:
                        record.__setattr__(key, value)
                record.__setattr__('updatedAt', str(int(time.time())))
                batch.put_item(Item=record._data)
            return True
        except Exception as e:
            raise Exception(e)
    
    @classmethod
    def _write_multiple_records(cls, values):
        ids = list(map(lambda v: v.get('id'), values))
        if not ids:
            return False
        records = cls._search([
            [
                'id', 'in', ids
            ]
        ])
        if not records:
            return False
        try:
            with cls._table.batch_writer() as batch:
                for record in records:
                    for item in values:
                        if record.id == item.get('id'):
                            for key, value in item.items():
                                if key not in DEFAULT_FIELDS \
                                        and key not in list(map(
                                    lambda field: field._name, cls._fields)
                                ):
                                    raise Exception(f'{key} does not exist')
                                if key not in DEFAULT_FIELDS:
                                    record.__setattr__(key, value)
                            record.__setattr__('updatedAt', str(int(time.time())))
                            batch.put_item(Item=record._data)
        except Exception as e:
            raise Exception(e)
        return True
    
    @classmethod
    def _update(cls, records):
        if isinstance(records, list):
            return cls._write_multiple_records(records)
        elif isinstance(records, dict):
            return cls._write_single_record(records)
        
    def delete(self, ids):
        return self._delete(ids)

    @classmethod
    def _delete(cls, ids):
        if isinstance(ids, str):
                try:
                    with cls._table.batch_writer() as batch:
                        batch.delete_item(Key={'id': ids})
                except Exception as e:
                    raise Exception(e)
                return RecordSet(cls)
        if isinstance(ids, list):
            if not ids:
                try:
                    with cls._table.batch_writer() as batch:
                        for key, record in enumerate(cls._records):
                            batch.delete_item(Key={'id': record.get('id')})
                except Exception as e:
                    raise Exception(e)
                cls._records = []
                return RecordSet(cls)
            try:
                with cls._table.batch_writer() as batch:
                    for id in ids:
                        batch.delete_item(Key={'id': id})
            except Exception as e:
                raise Exception(e)
        return RecordSet(cls)
    
    def next(self, last_evaluated_key):
        pass

    def previous(self, last_evaluated_key):
        pass
