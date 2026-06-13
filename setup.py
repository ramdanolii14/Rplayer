from setuptools import setup

setup(
    name='IDR Spectrum Player',
    version='1.0.0',
    author='Ramdan Olii',
    description='Native audio player with real-time spectrum visualization and IDR/USD exchange rate chart',
    py_modules=['idr_spectrum_player'],
    entry_points={
        'console_scripts': [
            'idr-spectrum=idr_spectrum_player:main',
        ],
        'gui_scripts': [
            'idr-spectrum-gui=idr_spectrum_player:main',
        ]
    },
    install_requires=[
        'PyGObject>=3.46.0',
    ],
    python_requires='>=3.11',
)
