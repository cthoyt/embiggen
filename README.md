Embiggen
=========================================================================================
|pip| |downloads| |tutorials| |documentation| |python_version| |DOI| |license|

Embiggen is the graph machine learning submodule of the [GraPE](https://github.com/AnacletoLAB/grape) library.

How to install Embiggen
-------------------------
To install the complete GraPE library, do run:

```bash
    pip install grape
```

Instead, to exclusively install the Embiggen package, you can run:

```bash
    pip install embiggen
```

Unit testing
-----------------------------------
To run the unit testing on the package, generating
the coverage and the HTML report, you can use:

```bash
    pytest --cov embiggen --cov-report html
```

Cite GraPE
----------------------------------------------
Please cite the following paper if it was useful for your research:

.. code:: bib

    @misc{cappelletti2021grape,
      title={GraPE: fast and scalable Graph Processing and Embedding}, 
      author={Luca Cappelletti and Tommaso Fontana and Elena Casiraghi and Vida Ravanmehr and Tiffany J. Callahan and Marcin P. Joachimiak and Christopher J. Mungall and Peter N. Robinson and Justin Reese and Giorgio Valentini},
      year={2021},
      eprint={2110.06196},
      archivePrefix={arXiv},
      primaryClass={cs.LG}
    }

.. |pip| image:: https://badge.fury.io/py/embiggen.svg
    :target: https://badge.fury.io/py/embiggen
    :alt: Pypi project

.. |downloads| image:: https://img.shields.io/badge/Documentation-blue.svg
    :target: https://pepy.tech/badge/embiggen
    :alt: Pypi total project downloads

.. |license| image:: https://img.shields.io/badge/License-BSD3-blue.svg
    :target: https://opensource.org/licenses/BSD-3-Clause
    :alt: License

.. |tutorials| image:: https://img.shields.io/badge/Tutorial-Jupyter%20Notebooks-blue.svg
    :target: https://github.com/AnacletoLAB/grape/tree/main/tutorials
    :alt: Tutorials

.. |documentation| image:: https://img.shields.io/badge/Documentation-Available%20here-blue.svg
    :target: https://anacletolab.github.io/grape/index.html
    :alt: Documentation

.. |DOI| image:: https://img.shields.io/badge/DOI-10.48550/arXiv.2110.06196-blue.svg
    :target: https://doi.org/10.48550/arXiv.2110.06196
    :alt: DOI

.. |python_version| image:: https://img.shields.io/badge/Python-3.6+-blue.svg
    :target: https://pypi.org/project/embiggen/#history
    :alt: Supported Python versions