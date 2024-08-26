"""
Django settings for labmanager project.

Generated by 'django-admin startproject' using Django 3.2.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

from pathlib import Path
import os
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-&-cy7#2$1@3lin26-q-j4vi=8$x756y0kilqptr@+d^y2je+e+'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [ 
    "localhost",
    "labmanager.apps1-fm-int.icloud.intel.com",
    "labspace.apps1-bg-int.icloud.intel.com",
    "labspaceapiProdBG-Clone.apps1-bg-int.icloud.intel.com",
    "sivindicator.intel.com",
    "127.0.0.1",
    "10.254.0.78",
    "labspaceapi.apps1-bg-int.icloud.intel.com",
    "lapspace.apps1-or-int.icloud.intel.com",
    "labspace.iglb.intel.com",
    "labspace.intel.com",
    "labspaceapi.apps1-or-int.icloud.intel.com"
   ]
CORS_ALLOWED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:4200',
    'http://localhost:8000',
    'http://127.0.0.1:4200',
    'https://labmanager.apps1-fm-int.icloud.intel.com',
    'https://sivindicator.intel.com',
    "https://labspace.apps1-bg-int.icloud.intel.com",
    "https://labspaceapi.apps1-bg-int.icloud.intel.com",
    "https://lapspace.apps1-or-int.icloud.intel.com",
    "https://labspace.iglb.intel.com",
    "https://labspace.intel.com",
    "https://labspaceapi.apps1-or-int.icloud.intel.com", 
]
CORS_ALLOW_HEADERS = [ '*',
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    'access-control-allow-methods',
    'Access-Control-Allow-Origin',
]
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_CREDENTIALS = True
# Application definition
CORS_ORIGIN_ALLOW_ALL=True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'allocationapp',
    'rest_framework.authtoken',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = 'labmanager.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'labmanager.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases
'''
DATABASES = {
    'default': {
        'ENGINE': 'djongo',
        'NAME': 'WorkbenchAllocation',
    }
}
'''
DATABASES = {
    'default':{
        'ENGINE':'djongo',
        'NAME':'LabManagerProd',
        'ENFORCE_SCHEMA':False,
        'CLIENT':{
            'host':'mongodb://LabManagerProd_rw:81bM4Vy2o5vTgY8@p1pg1mon011.gar.corp.intel.com:7076,p2pg1mon011.gar.corp.intel.com:7076,dr1bgmon011pg1.gar.corp.intel.com:7076/LabManagerProd?ssl=true&replicaSet=mongo7076'
        }
    }
}


# DATABASES = {
#     'default':{
#         'ENGINE':'djongo',
#         'NAME':'LabManagerProdClone',
#         'ENFORCE_SCHEMA':False,
#         'CLIENT':{
#             'host':'mongodb://LabManagerProdClone_rw:rRlS0XfG212A8C0@p1fm1mon288.amr.corp.intel.com:9051,p2fm1mon288.amr.corp.intel.com:9051,p3fm1mon288.amr.corp.intel.com:9051/LabManagerProdClone?ssl=true&replicaSet=mongo9051'
#         }
#     }
# }


# DATABASES = {
#     'default':{
#         'ENGINE':'djongo',
#         'NAME':'LabManager',
#         'ENFORCE_SCHEMA':False,
#         'CLIENT':{
#             'host':'mongodb://LabManager_rw:tUsG2KwR3ChDh91@d1fm1mon229.amr.corp.intel.com:8621,d2fm1mon229.amr.corp.intel.com:8621,d3fm1mon229.amr.corp.intel.com:8621/LabManager?ssl=true&replicaSet=mongo8621'
#         }
#     }
# }

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR,'static')
# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


LOGGING = {
	'version':1,
	'disable_existing_loggers': False,
	'formatters':{
		'large':{
			'format':'%(levelname)s %(asctime)s %(module)s %(funcName)s %(lineno)s %(message)s'
		},
		'tiny':{
			'format':'%(asctime)s  %(message)s  '
		}
	},
	'handlers':{
        'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
            'formatter':'large',
        },
		'errors_file':{
			'level':'ERROR',
		       'class':'logging.handlers.RotatingFileHandler',
			'filename': os.path.join(BASE_DIR,'logs/ErrorLoggers.log'),
			'formatter':'large',
		},
		'info_file':{
			'level':'INFO',
		       'class':'logging.handlers.RotatingFileHandler',
			'filename':os.path.join(BASE_DIR,'logs/InfoLoggers.log'),
			'formatter':'large',
		},
        'scheduler_file':{
            'level':'INFO',
            'class':'logging.handlers.RotatingFileHandler',
			'filename':os.path.join(BASE_DIR,'logs/SchedulerLoggers.log'),
			'formatter':'large',

        }
	},
	'loggers':{
        'django':{
            "handlers":["console"],
            "propagate":True,
            "level":"INFO"
        },
		'error_logger':{
			'handlers':['errors_file'],
			'level':'WARNING',
			'propagate':False,
		},
		'info_logger':{
			'handlers':['info_file'],
			'level':'INFO',
			'propagate':False,
		},
        'scheduler_logger':{
            'handlers':['scheduler_file'],
			'level':'INFO',
			'propagate':False,
        }
        
	},
}