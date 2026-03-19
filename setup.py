from setuptools import setup

setup(
    name='nerve',
    version='1.0',
    py_modules=['nerve', 'metrics', 'ui'],
    entry_points={
        'console_scripts': [
            'nerve=nerve:main',
        ],
    },
    install_requires=[
        'psutil',
        'colorama',
        'pywin32'
    ],
)
