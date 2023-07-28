import time
import uuid
import json

from odooless.clients import resource, client

defaultFields = ['id', 'createdAt', 'updatedAt', 'deleted']


def create_table(
        TableName=None,  # required
        Fields=None,
        BillingMode='PAY_PER_REQUEST',
):
    try:
        AttributeDefinitions = [
            {
                'AttributeName': 'id',
                'AttributeType': 'S'
            }
        ]
        create_params = {
            'TableName':TableName,
            'KeySchema':[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'
                }
            ],
            'BillingMode':BillingMode,
            'AttributeDefinitions':AttributeDefinitions,
        }

        indexFields = list(
            filter(
                lambda field: field.get('index'),
                Fields
            )
        )
        if indexFields:
            for field in indexFields:
                AttributeDefinitions.append({
                    'AttributeName': field.get('name'),
                    'AttributeType': field.get('type')
                })
            GlobalSecondaryIndexes = list(
                map(
                    lambda field: {
                        'IndexName': f'{field.get("name")}Index',
                        'KeySchema': [
                            {
                                'AttributeName': field.get('name'),
                                'KeyType': 'HASH'
                            },
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL',
                        },
                    },
                    indexFields
                )
            )
            create_params['GlobalSecondaryIndexes'] = GlobalSecondaryIndexes

        table = resource.create_table(
            **create_params
        )
        table.wait_until_exists()
    except Exception as e:
        raise Exception(e)

    return True


def create_global_indexes(TableName, indexes):
    for field in indexes:
        AttributeDefinitions = []
        GlobalSecondaryIndexUpdates = []
        AttributeDefinitions.append({
            'AttributeName': field.get('name'),
            'AttributeType': field.get('type')
        })
        GlobalSecondaryIndexUpdates.append({
            'Create': {
                'IndexName': f'{field.get("name")}Index',
                'KeySchema': [
                    {
                        'AttributeName': field.get('name'),
                        'KeyType': 'HASH'
                    }
                    # Add more key schema attributes if needed
                ],
                'Projection': {
                    'ProjectionType': 'ALL'  # Projection type (e.g., ALL, KEYS_ONLY, INCLUDE)
                },
            }
        })
        table_description = client.describe_table(
            TableName=TableName
        )
        table_indexes = table_description.get('Table').get('GlobalSecondaryIndexes')
        if table_indexes:
            busy = list(
                filter(
                    lambda index: index.get('IndexStatus') != 'ACTIVE',
                    table_indexes
                )
            )
            if not busy:
                create_global_index(
                    TableName=TableName,
                    AttributeDefinitions=AttributeDefinitions,
                    GlobalSecondaryIndexUpdates=GlobalSecondaryIndexUpdates
                )
                try:
                    table_description = client.describe_table(
                        TableName=TableName
                    )
                    table_indexes = table_description.get('Table').get('GlobalSecondaryIndexes')
                    current_index = list(
                        filter(
                            lambda i: i.get('IndexName') == f'{field.get("name")}Index',
                            table_indexes
                        )
                    )
                    current_index_state = current_index[0].get('IndexStatus')
                except Exception as e:
                    raise Exception(e)
                while current_index_state != 'ACTIVE':
                    time.sleep(5)
                    try:
                        table_description = client.describe_table(
                            TableName=TableName
                        )
                        table_indexes = table_description.get('Table').get('GlobalSecondaryIndexes')
                        current_index = list(
                            filter(
                                lambda i: i.get('IndexName'),
                                table_indexes
                            )
                        )
                        current_index_state = current_index[0].get('IndexStatus')
                    except Exception as e:
                        raise Exception(e)
        create_global_index(
            TableName=TableName,
            AttributeDefinitions=AttributeDefinitions,
            GlobalSecondaryIndexUpdates=GlobalSecondaryIndexUpdates
        )
        try:
            table_description = client.describe_table(
                TableName=TableName
            )
            table_indexes = table_description.get('Table').get('GlobalSecondaryIndexes')
            current_index = list(
                filter(
                    lambda i: i.get('IndexName') == f'{field.get("name")}Index',
                    table_indexes
                )
            )
            current_index_state = current_index[0].get('IndexStatus')
        except Exception as e:
            raise Exception(e)
        while current_index_state != 'ACTIVE':
            time.sleep(5)
            try:
                table_description = client.describe_table(
                    TableName=TableName
                )
                table_indexes = table_description.get('Table').get('GlobalSecondaryIndexes')
                current_index = list(
                    filter(
                        lambda i: i.get('IndexName'),
                        table_indexes
                    )
                )
                current_index_state = current_index[0].get('IndexStatus')
            except Exception as e:
                raise Exception(e)
    return True


def create_global_index(TableName, AttributeDefinitions, GlobalSecondaryIndexUpdates):
    update_table(
        TableName=TableName,
        AttributeDefinitions=AttributeDefinitions,
        GlobalSecondaryIndexUpdates=GlobalSecondaryIndexUpdates
    )
    return


def remove_global_indexes(TableName, indexes):
    for index in indexes:
        AttributeDefinitions = [
            {
                'AttributeName': index.get('KeySchema')[0].get('AttributeName'),
                'AttributeType': 'S'
            }
        ]
        GlobalSecondaryIndexUpdates = [
            {
                'Delete': {
                    'IndexName': index.get('IndexName')
                }
            },
        ]
        table_description = client.describe_table(
            TableName=TableName
        )
        table_indexes = table_description.get('Table').get('GlobalSecondaryIndexes')
        if table_indexes:
            busy = list(
                filter(
                    lambda index: index.get('IndexStatus') != 'ACTIVE',
                    table_indexes
                )
            )
            if not busy:
                remove_global_index(
                    TableName=TableName,
                    AttributeDefinitions=AttributeDefinitions,
                    GlobalSecondaryIndexUpdates=GlobalSecondaryIndexUpdates
                )
                try:
                    table_description = client.describe_table(
                        TableName=TableName
                    )
                    table_indexes = table_description.get('Table').get('GlobalSecondaryIndexes')
                    current_index = list(
                        filter(
                            lambda i: i.get('IndexName') == index.get('IndexName'),
                            table_indexes
                        )
                    )
                except Exception as e:
                    raise Exception(e)
                while current_index:
                    time.sleep(5)
                    try:
                        table_description = client.describe_table(
                            TableName=TableName
                        )
                        table_indexes = table_description.get('Table').get('GlobalSecondaryIndexes')
                        current_index = list(
                            filter(
                                lambda i: i.get('IndexName'),
                                table_indexes
                            )
                        )
                    except Exception as e:
                        raise Exception(e)

        remove_global_index(
            TableName=TableName,
            AttributeDefinitions=AttributeDefinitions,
            GlobalSecondaryIndexUpdates=GlobalSecondaryIndexUpdates
        )
        try:
            table_description = client.describe_table(
                TableName=TableName
            )
            table_indexes = table_description.get('Table').get('GlobalSecondaryIndexes')
            current_index = list(
                filter(
                    lambda i: i.get('IndexName') == index.get('IndexName'),
                    table_indexes
                )
            )
        except Exception as e:
            raise Exception(e)
        while current_index:
            time.sleep(5)
            try:
                table_description = client.describe_table(
                    TableName=TableName
                )
                table_indexes = table_description.get('Table').get('GlobalSecondaryIndexes')
                current_index = list(
                    filter(
                        lambda i: i.get('IndexName'),
                        table_indexes
                    )
                )
            except Exception as e:
                raise Exception(e)
    return


def remove_global_index(TableName, AttributeDefinitions, GlobalSecondaryIndexUpdates):
    update_table(
        TableName=TableName,
        AttributeDefinitions=AttributeDefinitions,
        GlobalSecondaryIndexUpdates=GlobalSecondaryIndexUpdates
    )
    return


def update_table(
        TableName=None, # required
        AttributeDefinitions=None,
        GlobalSecondaryIndexUpdates=None,
):
    try:
        table = resource.Table(TableName)
        table.update(
            AttributeDefinitions=AttributeDefinitions,
            GlobalSecondaryIndexUpdates=GlobalSecondaryIndexUpdates,
        )
    except Exception as e:
        raise Exception(e)
    return


class RecordSet:
    def __init__(self, model):
        self.model = model
        self.records = model.records
        self.LastEvaluatedKey = model.LastEvaluatedKey

    def __iter__(self):
        return iter(self.records)

    def __len__(self):
        return len(self.records)

    def __getitem__(self, index):
        return self.records[index]

    def __str__(self):
        ids = ''
        for rec in self.records:
            ids += f'{rec.id}, '
        return f"<RecordSet {self.model._name}({ids})>"


class Model:
    records = None
    _name = None
    _table = None
    _fields = None
    _limit = 80
    _tags = None
    _scan_index_forward = True
    _billing_mode = 'PAY_PER_REQUEST'
    _provisioned_throughput = None
    _deletion_protection_enabled = False
    _records = None
    LastEvaluatedKey = None

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def _bootstrap(cls):
        try:
            cls._table = resource.Table(cls._name)
            attribute_definitions = cls._table.attribute_definitions
            global_indexes = cls._table.global_secondary_indexes

            tableFields = list(
                map(
                    lambda field: field.get('AttributeName'),
                    attribute_definitions
                )
            )
            fields_to_create = list(
                filter(
                    lambda field: field.get('name') not in tableFields and field.get('index'),
                    cls._fields
                )
            )
            modelFields = list(
                map(
                    lambda field: field.get('name'),
                    cls._fields
                )
            )
            if global_indexes:
                indexes_to_delete = list(
                    filter(
                        lambda index: index.get('IndexName').replace('Index', '') not in modelFields,
                        global_indexes
                    )
                )
                if indexes_to_delete:
                    remove_global_indexes(cls._name, indexes_to_delete)

            if fields_to_create:
                create_global_indexes(cls._name, fields_to_create)
        except Exception as e:
            create_table(cls._name, cls._fields)

    def create(self, values):
        return self._create(values)

    def read(self, ids, fields=None):
        return self._read(ids, fields)

    def write(self, values):
        return self._write(values)

    def delete(self, ids):
        return self._delete(ids)

    def search(self, domain=None, fields=None, offset=None, limit=None, sort='asc', **kwargs):
        if sort == 'asc':
            scan_index_forward = True
            return self._query(
                FilterExpression=domain,
                ProjectionExpression=fields,
                Limit=limit,
                ScanIndexForward=scan_index_forward,
                ExclusiveStartKey=offset,
                **kwargs
            )
        if sort == 'desc':
            scan_index_forward = False
            return self._query(
                FilterExpression=domain,
                ProjectionExpression=fields,
                Limit=limit,
                ScanIndexForward=scan_index_forward,
                ExclusiveStartKey=offset,
                **kwargs
            )
        else:
            raise ValueError

    def count(self):
        recs = self._scan(ProjectionExpression='id')
        return len(recs)

    def search_count(self, domain=None, **kwargs):
        if not kwargs:
            print('scanning')
            recs = self._scan(
                FilterExpression=domain,
                ProjectionExpression='id'
            )
            return len(recs)
        count = 0
        recs = self._query(FilterExpression=domain, ProjectionExpression='id', **kwargs)
        while recs.LastEvaluatedKey:
            count = count + len(recs)
            recs = self._query(
                FilterExpression=domain,
                ProjectionExpression='id',
                ExclusiveStartKey=recs.LastEvaluatedKey,
                **kwargs
            )
        count = count + len(recs)
        return count

    @classmethod
    def _create(cls, values):
        cls.records = []
        if isinstance(values, dict):
            try:
                cls._table = resource.Table(cls._name)
                values['id'] = str(uuid.uuid4())
                values['createdAt'] = str(time.time())
                values['updatedAt'] = str(time.time())
                cls._table.put_item(Item=values)
            except Exception as e:
                raise Exception(e)
            return cls(**values)
        if isinstance(values, list):
            try:
                cls._table = resource.Table(cls._name)
                with cls._table.batch_writer() as batch:
                    for value in values:
                        existingFields = list(map(lambda field: field.get('name'), cls._fields))
                        for key, val in value.items():
                            if key not in existingFields and key not in ['id', 'createdAt', 'updatedAt']:
                                raise Exception(f'Invalid field {key}')
                        value['id'] = str(uuid.uuid4())
                        value['createdAt'] = str(time.time())
                        value['updatedAt'] = str(time.time())
                        batch.put_item(Item=value)
                        cls.records.append(cls(**value))
            except Exception as e:
                raise Exception(e)
        recordSet = RecordSet(cls)
        return recordSet

    @classmethod
    def _read(cls, ids, fields=None):
        cls.records = []
        try:
            if isinstance(ids, list):
                Keys = list(
                    map(
                        lambda ID: {'id': ID},
                        ids
                    )
                )
            else:
                Keys = [
                    {
                        'id': ids
                    }
                ]

            payload = {
                'Keys': Keys,
            }
            if fields:
                payload['ProjectionExpression'] = f''
                for key, value in enumerate(fields):
                    if key < len(fields) - 1:
                        payload['ProjectionExpression'] += f'{value}, '
                    else:
                        payload['ProjectionExpression'] += f'{value}'

            RequestItems={
                f'{cls._name}': payload
            }

            response = resource.batch_get_item(
                RequestItems=RequestItems
            )

            # Get the items from the response
            items = response['Responses'][cls._name]

            for item in items:
                cls.records.append(cls(**item))
            recordSet = RecordSet(cls)
            return recordSet
        except Exception as e:
            raise Exception(e)

    @classmethod
    def _write(cls, values):
        try:
            cls._table = resource.Table(cls._name)
            with cls._table.batch_writer() as batch:
                if isinstance(values, list):
                    recs = cls._read(
                        list(
                            map(
                                lambda rec: rec.get('id'),
                                values
                            )
                        )
                    )
                    for rec in recs:
                        for item in values:
                            if rec.id == item.get('id'):
                                for key, value in item.items():
                                    if key not in defaultFields \
                                            and key not in list(map(
                                        lambda field: field.get('name'), cls._fields)
                                    ):
                                        raise Exception(f'{key} does not exist')
                                    setattr(rec, key, value)
                                    setattr(rec, 'updatedAt', str(time.time()))
                        Item = rec.__dict__
                        Item.pop('_table', None)
                        batch.put_item(Item=Item)

                elif isinstance(values, dict):
                    recs = cls._read([values.get('id')])
                    for key, value in values.items():
                        if key not in defaultFields \
                                and key not in list(map(
                            lambda field: field.get('name'), cls._fields)
                        ):
                            raise Exception(f'{key} does not exist')
                        setattr(recs[0], key, value)
                        setattr(recs[0], 'updatedAt', str(time.time()))
                    Item = recs[0].__dict__
                    Item.pop('_table', None)
                    batch.put_item(Item=Item)
            return True
        except Exception as e:
            raise Exception(e)

    @classmethod
    def process_filter_expression(cls, filter_expression):
        FilterExpression = ''
        ExpressionAttributeNames = {}
        ExpressionAttributeValues = {}
        for key, expression in enumerate(filter_expression):
            if key < len(filter_expression) - 1:
                if isinstance(expression, list):
                    attribute = expression[0]
                    operator = expression[1]
                    if operator in ['=', '<>', '<', '<=', '>', '>=']:
                        ExpressionAttributeValues[f':{attribute}'] = expression[2]
                        ExpressionAttributeNames[f'#{attribute}'] = attribute
                        FilterExpression += f"#{attribute} {operator} :{attribute} "
                    if operator.upper() == 'IN':
                        if isinstance(expression[2], list):
                            operand = f''
                            for k, v in enumerate(expression[2]):
                                if k < len(expression[2]) - 1:
                                    operand += f':{attribute}{k},'
                                else:
                                    operand += f':{attribute}{k}'
                                ExpressionAttributeValues[f':{attribute}{k}'] = v
                            operand = f'({operand})'
                            FilterExpression += f"#{attribute} {operator.upper()} {operand} "
                            ExpressionAttributeNames[f'#{attribute}'] = f'{attribute}'
                        else:
                            raise ValueError
                    if operator.upper() == 'BETWEEN':
                        if isinstance(expression[2], list) and len(expression[2]) == 2:
                            operand = f'{expression[2][0]} AND {expression[2][1]}'
                            FilterExpression += f'#{attribute} {operator.upper()} :{attribute}'
                        else:
                            raise ValueError
                        ExpressionAttributeNames[f'#{attribute}'] = f'{attribute}'
                        ExpressionAttributeValues[f':{attribute}'] = f'{operand}'
                if isinstance(expression, str) and expression.upper() in ['AND', 'OR']:
                    FilterExpression += f'{expression.upper()} '
            else:
                if isinstance(expression, list):
                    attribute = expression[0]
                    operator = expression[1]
                    if operator in ['=', '<>', '<', '<=', '>', '>=']:
                        ExpressionAttributeValues[f':{attribute}'] = expression[2]
                        ExpressionAttributeNames[f'#{attribute}'] = attribute
                        FilterExpression += f"#{attribute} {operator} :{attribute} "
                    if operator.upper() == 'IN':
                        if isinstance(expression[2], list):
                            operand = f''
                            for k, v in enumerate(expression[2]):
                                if k < len(expression[2]) - 1:
                                    operand += f':{attribute}{k},'
                                else:
                                    operand += f':{attribute}{k}'
                                ExpressionAttributeValues[f':{attribute}{k}'] = v
                            operand = f'({operand})'
                            FilterExpression += f"#{attribute} {operator.upper()} {operand} "
                            ExpressionAttributeNames[f'#{attribute}'] = f'{attribute}'
                        else:
                            raise ValueError
                    if operator.upper() == 'BETWEEN':
                        if isinstance(expression[2], list) and len(expression[2]) == 2:
                            operand = f':{attribute}0 AND :{attribute}1'
                            FilterExpression += f'#{attribute} {operator.upper()} {operand} '
                        else:
                            raise ValueError
                        ExpressionAttributeNames[f'#{attribute}'] = f'{attribute}'
                        ExpressionAttributeValues[f':{attribute}0'] = f'{expression[2][0]}'
                        ExpressionAttributeValues[f':{attribute}1'] = f'{expression[2][1]}'
                else:
                    raise ValueError
        return FilterExpression, ExpressionAttributeNames, ExpressionAttributeValues

    @classmethod
    def _scan(cls, FilterExpression=None, ProjectionExpression='id'):
        cls.records = []
        cls._table = resource.Table(cls._name)
        scan_params = {}
        if FilterExpression:
            FilterExpression, ExpressionAttributeNames, ExpressionAttributeValues = cls.process_filter_expression(FilterExpression)
            scan_params['FilterExpression'] = FilterExpression
            scan_params['ExpressionAttributeNames'] = ExpressionAttributeNames
            scan_params['ExpressionAttributeValues'] = ExpressionAttributeValues

        if ProjectionExpression:
            scan_params['ProjectionExpression'] = ProjectionExpression
        response = cls._table.scan(**scan_params)
        while 'LastEvaluatedKey' in response:
            for item in response.get('Items'):
                cls.records.append(item)
            scan_params['ExclusiveStartKey'] = response.get('LastEvaluatedKey')
            response = cls._table.scan(**scan_params)
        for item in response.get('Items'):
            cls.records.append(cls(**item))
        return RecordSet(cls)

    @classmethod
    def _query(cls, FilterExpression=None, ProjectionExpression=None, Limit=None, ScanIndexForward=True, ExclusiveStartKey=None, **kwargs):
        if not kwargs:
            return cls._scan(FilterExpression=FilterExpression, ProjectionExpression=ProjectionExpression)
        cls.records = []
        cls._table = resource.Table(cls._name)
        first_key = next(iter(kwargs))
        IndexName = f'{first_key}Index'
        KeyConditionExpression = f'#{first_key} = :{first_key}'
        query_params = {
            'IndexName': IndexName,
            'KeyConditionExpression': KeyConditionExpression,
            'Limit': Limit if Limit else cls._limit,
            'ScanIndexForward': ScanIndexForward
        }

        ExpressionAttributeNames = {}
        ExpressionAttributeValues = {}
        if FilterExpression:
            FilterExpression, ExpressionAttributeNames, ExpressionAttributeValues = cls.process_filter_expression(FilterExpression)
            query_params['FilterExpression'] = FilterExpression
            query_params['ExpressionAttributeNames'] = ExpressionAttributeNames
            query_params['ExpressionAttributeNames'][f'#{first_key}'] = f'{first_key}'
            query_params['ExpressionAttributeValues'] = ExpressionAttributeValues
            query_params['ExpressionAttributeValues'][f':{first_key}'] = kwargs[first_key]
        else:
            query_params['ExpressionAttributeNames'] = ExpressionAttributeNames
            query_params['ExpressionAttributeValues'] = ExpressionAttributeValues
            query_params['ExpressionAttributeNames'][f'#{first_key}'] = f'{first_key}'
            query_params['ExpressionAttributeValues'][f':{first_key}'] = kwargs[first_key]

        if ProjectionExpression:
            query_params['ProjectionExpression'] = ProjectionExpression

        if ExclusiveStartKey:
            query_params['ExclusiveStartKey'] = ExclusiveStartKey

        response = cls._table.query(**query_params)
        for item in response.get('Items'):
            cls.records.append(cls(**item))
        cls.LastEvaluatedKey = response.get('LastEvaluatedKey')
        return RecordSet(cls)

    @classmethod
    def _search(cls, fields=None, limit=None, exclusive_start_key=None, scan_index_forward=None, **kwargs):
        if not kwargs:
            cls._scan()
        cls.records = []
        # if not kwargs:
        #     raise Exception('Missing or invalid index')
        first_key = next(iter(kwargs))
        IndexName = f'{first_key}Index'
        KeyConditionExpression = f'#{first_key} = :{first_key}'
        query_params = {
            'IndexName': IndexName,
            'KeyConditionExpression': KeyConditionExpression,
        }
        ExpressionAttributeNames = {}
        ExpressionAttributeValues = {}
        for key, value in kwargs.items():
            if key == 'FilterExpression':
                FilterExpression = ''
                count = 0
                for attributeName, operatorAndValue in value.items():
                    if count < len(value.items())-1:
                        for operator, attributeValue in operatorAndValue.items():
                            FilterExpression += f'#{attributeName} {operator} :{attributeName} AND '
                            ExpressionAttributeNames[f'#{attributeName}'] = f'{attributeName}'
                            ExpressionAttributeValues[f':{attributeName}'] = f'{attributeValue} '
                    else:
                        for operator, attributeValue in operatorAndValue.items():
                            FilterExpression += f'#{attributeName} {operator} :{attributeName} '
                            ExpressionAttributeNames[f'#{attributeName}'] = f'{attributeName}'
                            ExpressionAttributeValues[f':{attributeName}'] = f'{attributeValue}'
                    count = count + 1
                query_params['FilterExpression'] = FilterExpression
            else:
                ExpressionAttributeNames[f'#{key}'] = f'{key}'
                ExpressionAttributeValues[f':{key}'] = f'{value}'

        query_params['ExpressionAttributeNames'] = ExpressionAttributeNames
        query_params['ExpressionAttributeValues'] = ExpressionAttributeValues
        query_params['Limit'] = limit if limit else cls._limit
        query_params['ScanIndexForward'] = scan_index_forward if scan_index_forward is not None else cls._scan_index_forward
        if fields:
            query_params['ProjectionExpression'] = f''
            for key, value in enumerate(fields):
                if key < len(fields)-1:
                    query_params['ProjectionExpression'] += f'{value}, '
                else:
                    query_params['ProjectionExpression'] += f'{value}'

        if exclusive_start_key:
            query_params['ExclusiveStartKey'] = exclusive_start_key

        try:
            cls._table = resource.Table(cls._name)
            response = cls._table.query(**query_params)
        except Exception as e:
            raise Exception(e)
        for item in response.get('Items'):
            cls.records.append(cls(**item))
        recordSet = RecordSet(cls)
        return recordSet

    @classmethod
    def _delete(cls, ids):
        if isinstance(ids, int):
            _id = ids
            cls._table = resource.Table(cls._name)
            try:
                cls._table.delete_item(Key={'id': _id})
                return True
            except Exception as e:
                raise Exception(e)
        if isinstance(ids, list):
            cls._table = resource.Table(cls._name)
            try:
                with cls._table.batch_writer() as batch:
                    for _id in ids:
                        batch.delete_item(Key={'id': _id})
                return True
            except Exception as e:
                raise Exception(e)

    def paginate(self, exclusive_start_key, scan_index_forward):
        return self._paginate(exclusive_start_key, scan_index_forward)

    @classmethod
    def _paginate(cls, exclusive_start_key, scan_index_forward):
        cls._table = resource.Table(cls._name)

        return cls

    def next(self, exclusive_start_key):
        return self._next(exclusive_start_key)

    def _next(self, exclusive_start_key):
        return self._paginate(exclusive_start_key, True)

    def previous(self, exclusive_start_key, ):
        return self._previous(exclusive_start_key)

    def _previous(self, exclusive_start_key):
        return self._paginate(exclusive_start_key, False)


    @classmethod
    def _count(cls):
        count = 0
        cls._table = resource.Table(cls._name)
        ProjectionExpression = 'id'
        response = cls._table.scan(ProjectionExpression=ProjectionExpression)
        while 'LastEvaluatedKey' in response:
            items = response['Items']
            count += len(items)
            response = cls._table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'],
                ProjectionExpression=ProjectionExpression
            )
        items = response['Items']
        count += len(items)
        return count

    @classmethod
    def _search_count(cls, **kwargs):
        if not kwargs:
            return cls._count()
        first_key = next(iter(kwargs))
        IndexName = f'{first_key}Index'
        KeyConditionExpression = f'#{first_key} = :{first_key}'

        query_params = {
            'IndexName': IndexName,
            'KeyConditionExpression': KeyConditionExpression,
        }
        ExpressionAttributeNames = {}
        ExpressionAttributeValues = {}
        for key, value in kwargs.items():
            if key == 'FilterExpression':
                FilterExpression = ''
                count = 0
                for attributeName, operatorAndValue in value.items():
                    if count < len(value.items())-1:
                        for operator, attributeValue in operatorAndValue.items():
                            if operator == 'between':
                                pass
                            if operator == 'in':
                                pass
                            if operator == '':
                                pass
                            FilterExpression += f'#{attributeName} {operator} :{attributeName} AND '
                            ExpressionAttributeNames[f'#{attributeName}'] = f'{attributeName}'
                            ExpressionAttributeValues[f':{attributeName}'] = f'{attributeValue} '
                    else:
                        for operator, attributeValue in operatorAndValue.items():
                            FilterExpression += f'#{attributeName} {operator} :{attributeName} '
                            ExpressionAttributeNames[f'#{attributeName}'] = f'{attributeName}'
                            ExpressionAttributeValues[f':{attributeName}'] = f'{attributeValue}'
                    count = count + 1
                query_params['FilterExpression'] = FilterExpression
            else:
                ExpressionAttributeNames[f'#{key}'] = f'{key}'
                ExpressionAttributeValues[f':{key}'] = f'{value}'

        query_params['ExpressionAttributeNames'] = ExpressionAttributeNames
        query_params['ExpressionAttributeValues'] = ExpressionAttributeValues
        query_params['ProjectionExpression'] = 'id'
        count = 0
        table = resource.Table(cls._name)
        response = table.query(**query_params)
        while 'LastEvaluatedKey' in response:
            items = response['Items']
            count += len(items)
            query_params['ExclusiveStartKey'] = response['LastEvaluatedKey']
            response = table.scan(**query_params)
        items = response['Items']
        count += len(items)
        return count
