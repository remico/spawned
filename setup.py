import setuptools
from spawned.spawned import Spawned


with open("README.md") as f:
    long_description = f.read()


# make the distribution platform dependent
try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
    class bdist_wheel(_bdist_wheel):
        def finalize_options(self):
            _bdist_wheel.finalize_options(self)
            self.root_is_pure = False
except ImportError:
    bdist_wheel = None


setuptools.setup(
    name="spawned",
    version=Spawned.do("cat **/VERSION"),
    author="remico",
    author_email="remicollab@gmail.com",
    description="A simple python module for dealing with sub-processes",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/remico/spawned",
    packages=setuptools.find_packages(exclude=['sndbx', 'test', 'tests']),
    package_data={'': ['VERSION']},
    py_modules=[],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Shells",
    ],
    python_requires='>=3.8',
    install_requires=['pexpect', 'setuptools'],
    license='GPLv3',
    platforms=['POSIX'],
    cmdclass={'bdist_wheel': bdist_wheel},
)
