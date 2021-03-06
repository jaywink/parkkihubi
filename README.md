# Parking hub

Django-based REST API for processing parking data.

## Requirements

* Python 3.x
* PostgreSQL + PostGIS

## Development

### Install required system packages

#### PostgreSQL

    # Ubuntu 16.04
    sudo apt-get install python3-dev libpg-dev postgresql postgis
    
#### GeoDjango extra packages

    # Ubuntu 16.04
    sudo apt-get install binutils libproj-dev gdal-bin

### Creating a virtualenv

Create a Python 3.x virtualenv either using the traditional `virtualenv` tool or using the great `virtualenvwrapper` toolset. Assuming the former, [once installed](https://virtualenvwrapper.readthedocs.io/en/latest/), simply do:

    mkvirtualenv -p /usr/bin/python3 parkkihubi

The virtualenv will automatically activate. To activate it in the future, just do:

    workon parkkihubi

### Python requirements

Use `pip-tools` to install and maintain installed dependencies.

    pip install -U pip  # pip-tools needs pip==6.1 or higher (!)
    pip install pip-tools

Install requirements as follows

    pip-sync requirements.txt requirements-dev.txt

### Django configuration

Environment variables are used to customize configuration in `parkkihubi/settings.py`. If you wish to override any settings, you can place them in a local `.env` file which will automatically be sourced when Django imports the settings file.

Create a basic file for development as follows

    echo 'DEBUG=True' > .env

### Database

Create user and database

    sudo -u postgres createuser -P -R -S parkkihubi  # use password `parkkihubi`
    sudo -u postgres createdb -O parkkihubi parkkihubi
    sudo -u postgres psql parkkihubi -c "CREATE EXTENSION postgis;"

Tests also require that PostGIS extension is installed on the test database. This can be achieved most easily by adding PostGIS extension to the default template: 

    sudo -u postgres psql -d template1 -c "CREATE EXTENSION IF NOT EXISTS postgis;"

Run migrations

    python manage.py migrate

### Updating requirements files

Use `pip-tools` to update the `requirements*.txt` files.

    pip install -U pip  # pip-tools needs pip==6.1 or higher (!)
    pip install pip-tools
    
When you change requirements, set them in `requirements.in` or `requirements-dev.in`. Then run:

    pip-compile requirements.in
    pip-compile requirements-dev.in
    
### Running tests

Run all tests

    py.test
    
Run with coverage

    py.test --cov-report html --cov .
    
Open `htmlcov/index.html` for the coverage report.

### Starting a development server

    python manage.py runserver

Operator API will be available at [http://127.0.0.1:8000/operator/v1/](http://127.0.0.1:8000/operator/v1/)

Internal API will be available at [http://127.0.0.1:8000/internal/v1/](http://127.0.0.1:8000/internal/v1/)

## License

[MIT](https://tldrlegal.com/license/mit-license)
