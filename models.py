import time
import uuid

from clients import resource

defaultFields = ['id', 'createdAt', 'updatedAt']


def bootstrap(name, fields, billing_mode='PAY_PER_REQUEST'):
    try:
        table = resource.Table(name)
        tableFields = list(map(lambda field: field.get('AttributeName'), table.attribute_definitions))
        missingFields = list(filter(lambda field: field.get('name') not in tableFields and field.get('index'), fields))
        if missingFields:
            AttributeDefinitions = []
            GlobalSecondaryIndexUpdates = []
            for field in missingFields:
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
            table.update(
                AttributeDefinitions=AttributeDefinitions,
                GlobalSecondaryIndexUpdates=GlobalSecondaryIndexUpdates,
            )
        return table
    except Exception as e:
        try:
            AttributeDefinitions = [
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                }
            ]
            indexFields = list(filter(lambda field: field.get('index'), fields))
            for field in indexFields:
                AttributeDefinitions.append({
                    'AttributeName': field.get('name'),
                    'AttributeType': field.get('type')
                })
            GlobalSecondaryIndexes = list(map(lambda field: {
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
            }, indexFields))
            table = resource.create_table(
                TableName=name,
                KeySchema=[
                    {
                        'AttributeName': 'id',
                        'KeyType': 'HASH'
                    }
                ],
                BillingMode=billing_mode,
                AttributeDefinitions=AttributeDefinitions,
                GlobalSecondaryIndexes=GlobalSecondaryIndexes,
            )
            table.wait_until_exists()
            return table
        except Exception as e:
            raise Exception(e)


class RecordSet:
    def __init__(self, model, records):
        self.model = model
        self.records = records

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
        return f"<RecordSet {self.model}({ids})>"

    def search(self, domain=None):
        # Your search logic here
        # Return a new RecordSet instance with the filtered records
        filtered_records = self._apply_domain(domain)
        return RecordSet(self.model, filtered_records)

    def _apply_domain(self, domain):
        # Apply the domain filter to the records
        # and return the filtered records
        if domain is None:
            return self.records

        # Your domain filtering implementation
        filtered_records = [record for record in self.records if self._check_domain(record, domain)]
        return filtered_records

    def _check_domain(self, record, domain):
        # Your domain filtering logic
        # Implement the domain comparison for each field
        # in the record and return True or False
        pass

    def create(self, values):
        # Create a new record with the given values
        # and return the updated RecordSet instance
        # after adding the new record
        new_record = self.model(**values)
        self.records.append(new_record)
        return self

    def write(self, values):
        # Update the existing records with the given values
        # and return the updated RecordSet instance
        # after modifying the records
        for record in self.records:
            for field, value in values.items():
                setattr(record, field, value)
        return self

    def delete(self):
        # Delete the records from the RecordSet
        self.records = []

    def print_records(self):
        # Print the records in the RecordSet
        for record in self.records:
            print(record)


class Model:
    _name = None
    _table = None
    _fields = None
    _billing_mode = 'PAY_PER_REQUEST'
    _limit = 1

    def __init__(self, **kwargs):
        self.id = None
        for key, value in kwargs.items():
            setattr(self, key, value)

    # def __setitem__(self, key, value):
    #     self[key] = value

    def create(self, values):
        print(values)
        existingFields = list(map(lambda field: field.get('name'), self._fields))
        if isinstance(values, list):
            for value in values:
                for key, val in value.items():
                    if key not in existingFields and key != 'id':
                        raise Exception(f'Invalid field {key}')
                if not value.get('id'):
                    value['id'] = str(uuid.uuid4())
            return self._create(values)
        if isinstance(values, dict):
            for key, val in values.items():
                if key not in existingFields and key != 'id':
                    raise Exception(f'Invalid field {key}')
            if not values.get('id'):
                values['id'] = str(uuid.uuid4())
            return self._create(values)

    @classmethod
    def _create(cls, values):
        records = []
        if isinstance(values, list):
            try:
                cls._table = bootstrap(
                    cls._name,
                    cls._fields,
                    cls._billing_mode
                ) if cls._name else None
                with cls._table.batch_writer() as batch:
                    for value in values:
                        existingFields = list(map(lambda field: field.get('name'), cls._fields))
                        for key, val in value.items():
                            if key not in existingFields and key != 'id':
                                raise Exception(f'Invalid field {key}')
                        value['createdAt'] = str(time.time())
                        value['updatedAt'] = str(time.time())
                        batch.put_item(Item=value)
                        records.append(cls(**value))
            except Exception as e:
                raise Exception(e)
        if isinstance(values, dict):
            try:
                cls._table = bootstrap(
                    cls._name,
                    cls._fields,
                    cls._billing_mode
                ) if cls._name else None

                values['createdAt'] = str(time.time())
                values['updatedAt'] = str(time.time())
                response = cls._table.put_item(Item=values)
                records.append(cls(**values))
            except Exception as e:
                raise Exception(e)
        return records

    def read(self, IDs=None, fields=None):
        IDs = IDs if IDs else self.id
        if not IDs:
            raise Exception('Missing IDs')
        return self._read(IDs, fields)

    @classmethod
    def _read(cls, IDS, fields=None):
        Keys = list(map(lambda ID: {'id': ID}, IDS))
        try:
            cls._table = bootstrap(
                cls._name,
                cls._fields,
                cls._billing_mode
            ) if cls._name else None
            AttributeDefinitionsList = list(
                filter(
                    lambda filteredAttribute: 'password' not in filteredAttribute and 'secret' not in filteredAttribute,
                    map(
                        lambda attribute: attribute.get('AttributeName'),
                        cls._table.meta.data.get('AttributeDefinitions')
                    )
                )
            )
            ProjectionExpression = ''
            AttributeDefinitions = {}

            if fields:
                for key, attibute in enumerate(fields):
                    AttributeDefinitions[f'#{attibute}'] = attibute
                    ProjectionExpression += f'#{attibute}, ' if key < len(
                        AttributeDefinitionsList) - 1 else f'#{attibute}'

            response = resource.batch_get_item(
                RequestItems={
                    cls._name: {
                        'Keys': Keys,
                    }
                }
            )
            items = response['Responses'][cls._name]
            results = []
            for item in items:
                instance = cls()
                for key, value in item.items():
                    setattr(instance, key, value)
                results.append(instance)
            return results
        #            return items
        except Exception as e:
            raise Exception(e, 'line 268')

    def write(self, values):
        if isinstance(values, list):
            if any([not id for id in list(map(lambda item: item.id, values))]):
                raise Exception('One record or more missing id')
            self._write(values)
        elif isinstance(values, dict):
            if 'id' not in values and not self.id:
                raise Exception('Missing id or not single record')
            for key, value in values.items():
                setattr(self, key, value)
            return self._write(self.__dict__)
        else:
            return False

    @classmethod
    def _write(cls, values):
        try:
            cls._table = bootstrap(
                cls._name,
                cls._fields,
                cls._billing_mode
            ) if cls._name else None
            with cls._table.batch_writer() as batch:
                if isinstance(values, list):
                    recs = cls._read(list(map(lambda rec: rec.id, values)))
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

                                #                                    rec[key] = value
                                #                                    rec['updatedAt'] = str(time.time())
                                batch.put_item(Item=rec.__dict__)
                elif isinstance(values, dict):
                    recs = cls._read(IDS=[values.get('id')])
                    for key, value in values.items():
                        if key not in defaultFields \
                                and key not in list(map(
                            lambda field: field.get('name'), cls._fields)
                        ):
                            raise Exception(f'{key} does not exist')
                        setattr(recs[0], key, value)
                        setattr(recs[0], 'updatedAt', str(time.time()))

                    #                        recs[0][key] = value
                    #                        recs[0]['updatedAt'] = str(time.time())
                    print(recs[0].__dict__)
                    batch.put_item(Item=recs[0].__dict__)
                else:
                    return False
            return True
        except Exception as e:
            raise Exception(e)

    def delete(self, ids=None):
        ids = ids if ids else []
        if not ids:
            if not self.id:
                return False
            ids.append(self.id)
        return self._delete(ids)

    @classmethod
    def _delete(cls, ids=None):
        try:
            if not ids:
                return False
            cls._table = bootstrap(
                cls._name,
                cls._fields,
                cls._billing_mode
            ) if cls._name else None
            with cls._table.batch_writer() as batch:
                for ID in ids:
                    batch.delete_item(Key={'id': ID})
            return True
        except Exception as e:
            raise Exception(e)

    def to_record(self):
        return self

    def search(self, gsi_domain=None, fields=None, limit=None):
        recs = self._search(gsi_domain, fields, limit)
        record_set = RecordSet(self._name, recs)
        return record_set

    @classmethod
    def _search(cls, gsi_domain=None, fields=None, limit=None):
        try:
            cls._table = bootstrap(
                cls._name,
                cls._fields,
                cls._billing_mode
            ) if cls._name else None
            TableName = cls._name
            ProjectionExpression = ''
            ExpressionAttributeNames = {}
            ExpressionAttributeValues = {}

            AttributeDefinitionsList = list(
                filter(
                    lambda
                        filteredAttribute: 'password' not in filteredAttribute and 'secret' not in filteredAttribute,
                    map(
                        lambda attribute: attribute.get('AttributeName'),
                        cls._table.meta.data.get('AttributeDefinitions')
                    )
                )
            )

            if fields:
                if 'id' not in fields:
                    fields.append('id')
                for key, field in enumerate(fields):
                    if field in AttributeDefinitionsList:
                        ExpressionAttributeNames[f'#{field}'] = field
                        ProjectionExpression += f'#{field}, ' if key < len(
                            fields) - 1 else f'#{field}'

            if not gsi_domain:
                scan_params = {
                    'TableName': TableName,
                    'Limit': cls._limit if not limit else limit,
                    'ProjectionExpression': ProjectionExpression,
                    'ExpressionAttributeNames': ExpressionAttributeNames
                }
                response = cls._table.scan(**scan_params)
                items = response.get('Items', [])
                results = []
                for item in items:
                    instance = cls()
                    for key, value in item.items():
                        setattr(instance, key, value)
                    results.append(instance)
                return results
            for domain in gsi_domain:
                if domain[0] not in AttributeDefinitionsList:
                    raise Exception(f'{domain[0]} is not an index field')
                ExpressionAttributeNames[f'#{domain[0]}'] = f'{domain[0]}'
                ExpressionAttributeValues[f':{domain[0]}'] = domain[2]

            IndexName = f'{gsi_domain[0][0]}Index'
            KeyConditionExpression = f'#{gsi_domain[0][0]} {gsi_domain[0][1]} :{gsi_domain[0][0]}'

            query_params = {
                'TableName': TableName,
                'IndexName': IndexName,
                'KeyConditionExpression': KeyConditionExpression,
                'ExpressionAttributeNames': ExpressionAttributeNames,
                'ExpressionAttributeValues': ExpressionAttributeValues,
                'Limit': cls._limit if not limit else limit,
            }
            response = cls._table.query(**query_params)
            items = response.get('Items', [])
            results = []
            for item in items:
                instance = cls()
                for key, value in item.items():
                    setattr(instance, key, value)
                results.append(instance)
            return results
        except Exception as e:
            raise Exception(e)

    def search_read(self, gsi_domain=None, fields=None, limit=_limit):
        return self._search_read(gsi_domain, fields, limit)

    @classmethod
    def _search_read(cls, gsi_domain=None, fields=None, limit=None):
        try:
            cls._table = bootstrap(
                cls._name,
                cls._fields,
                cls._billing_mode
            ) if cls._name else None
            TableName = cls._name

            ProjectionExpression = ''
            ExpressionAttributeNames = {}
            ExpressionAttributeValues = {}

            AttributeDefinitionsList = list(
                filter(
                    lambda filteredAttribute:
                        'password' not in filteredAttribute and 'secret' not in filteredAttribute,
                    map(
                        lambda attribute: attribute.get('AttributeName'),
                        cls._table.meta.data.get('AttributeDefinitions')
                    )
                )
            )
            if fields:
                if 'id' not in fields:
                    fields.append('id')
                for key, field in enumerate(fields):
                    if field in AttributeDefinitionsList:
                        ExpressionAttributeNames[f'#{field}'] = field
                        ProjectionExpression += f'#{field}, ' if key < len(
                            fields) - 1 else f'#{field}'

            if not gsi_domain:
                scan_params = {
                    'TableName': TableName,
                    'Limit': cls._limit if not limit else limit,
                    'ProjectionExpression': ProjectionExpression,
                    'ExpressionAttributeNames': ExpressionAttributeNames
                }
                response = cls._table.scan(**scan_params)
                items = response.get('Items', [])
                results = []
                for item in items:
                    instance = cls()
                    for key, value in item.items():
                        setattr(instance, key, value)
                    results.append(instance.__dict__)
                return results

            for domain in gsi_domain:
                if domain[0] not in AttributeDefinitionsList:
                    raise Exception(f'{domain[0]} is not an index field')
                ExpressionAttributeNames[f'#{domain[0]}'] = f'{domain[0]}'
                ExpressionAttributeValues[f':{domain[0]}'] = domain[2]

            IndexName = f'{gsi_domain[0][0]}Index'
            KeyConditionExpression = f'#{gsi_domain[0][0]} {gsi_domain[0][1]} :{gsi_domain[0][0]}'

            query_params = {
                'TableName': TableName,
                'IndexName': IndexName,
                'KeyConditionExpression': KeyConditionExpression,
                'ExpressionAttributeNames': ExpressionAttributeNames,
                'ExpressionAttributeValues': ExpressionAttributeValues,
                'Limit': cls._limit if not limit else limit,
            }
            response = cls._table.query(**query_params)
            items = response.get('Items', [])
            results = []
            for item in items:
                instance = cls()
                for key, value in item.items():
                    setattr(instance, key, value)
                results.append(instance)
            return results
        except Exception as e:
            raise Exception(e)

