from setuptools import setup, find_packages
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name='odooless',
    version='0.1.15',
    description='A DynamoDB ORM inspired by Odoo',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Sam Hasan',
    author_email='sam@barameg.co',
    url='https://github.com/Barameg/odooless.git',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    keywords='odooless, dynamodb, orm, odoo',
    install_requires=[
        'boto3'
        # List any dependencies your package needs
    ],
    python_requires='>=3.6',
)

