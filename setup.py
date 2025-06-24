__author__ = 'samantha'

from setuptools import setup, find_packages

packages = find_packages(exclude=['tests'])
setup(name='uopserver',
      version='0.1',
      description='all in one python UOP package',
      author='Samantha Atkins',
      author_email='samantha@sjasoft.com',
      license='internal',
      packages=packages,
      install_requires=['uop', 'fastapi', 'uvicorn', 'pytest-asyncio',
                        'cryptography', 'aiohttp',
                        'aiohttp_session', 'aiohttp_cors', 'pyyaml', 'requests'],
      entry_points={
          'console_scripts': ['aioserve=uopserver.aio_serve.main:main']
      },
      zip_safe=False)
