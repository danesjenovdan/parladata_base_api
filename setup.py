from distutils.core import setup

requires = [
    "requests==2.32.3",
]


setup(
  name = 'Parladata Base Api',
  packages = ['parladata_base_api'],
  version = '1.0.0',
  license='CC0-1.0',
  package_dir={"": "parladata_base_api"},
  description = 'Cached api for parladata',
  author = 'Danes je nov dan',
  author_email = 'tech@danesjenovdan.si',
  url = 'https://github.com/danesjenovdan/parladata_base_api',
  download_url = 'https://github.com/danesjenovdan/parladata_base_api/archive/v_01.tar.gz',
  keywords = ['parladata', 'api'],
  install_requires=requires,
  classifiers=[
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'License :: CC0-1.0',
    'Programming Language :: Python :: 3',      #Specify which pyhton versions that you want to support
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: 3.11',
    'Programming Language :: Python :: 3.12',
  ],
)

