#!/usr/bin/env python

############################################################################
# Copyright (c) 2015-2017 Saint Petersburg State University
# Copyright (c) 2011-2015 Saint Petersburg Academic University
# All Rights Reserved
# See file LICENSE for details.
############################################################################

from __future__ import with_statement
import os
import sys
from glob import glob
from os.path import join, isfile, abspath, dirname, isdir
import shutil

from quast_libs import qconfig
qconfig.check_python_version()
from quast_libs import qutils

from quast_libs.log import get_logger
logger = get_logger(qconfig.LOGGER_DEFAULT_NAME)
logger.set_up_console_handler(debug=True)

try:
    from setuptools import setup, find_packages
except:
    logger.error('setuptools is not installed or outdated!\n\n'
                 'You can install or update setuptools using\n'
                 'pip install --upgrade setuptools (if you have pip)\n'
                 'or\n'
                 'sudo apt-get install python-setuptools (on Ubuntu)\n'
                 '\n'
                 'You may also use old-style installation scripts: ./install.sh or ./install_full.sh',
                 exit_with_code=1)

from quast_libs.glimmer import compile_glimmer
from quast_libs.gage import compile_gage
from quast_libs.run_busco import download_augustus, download_all_db
from quast_libs.search_references_meta import download_blast_binaries, download_blastdb
from quast_libs.ca_utils.misc import compile_aligner, compile_gnuplot
from quast_libs.ra_utils.misc import compile_reads_analyzer_tools, download_manta, compile_bwa, compile_bedtools

name = 'quast'
quast_package = qconfig.PACKAGE_NAME


args = sys.argv[1:]


def cmd_in(cmds):
    return any(c in args for c in cmds)


if abspath(dirname(__file__)) != abspath(os.getcwd()):
    logger.error('Please change to ' + dirname(__file__) + ' before running setup.py')
    sys.exit()


if cmd_in(['clean', 'sdist']):
    logger.info('Cleaning up binary files...')
    compile_aligner(logger, only_clean=True)
    compile_gnuplot(logger, only_clean=True)
    compile_glimmer(logger, only_clean=True)
    compile_gage(only_clean=True)
    compile_bwa(logger, only_clean=True)
    compile_bedtools(logger, only_clean=True)
    for fpath in [fn for fn in glob(join(quast_package, '*.pyc'))]: os.remove(fpath)
    for fpath in [fn for fn in glob(join(quast_package, 'html_saver', '*.pyc'))]: os.remove(fpath)
    for fpath in [fn for fn in glob(join(quast_package, 'site_packages', '*', '*.pyc'))]: os.remove(fpath)

    if cmd_in(['clean']):
        if isdir('build'):
            shutil.rmtree('build')
        if isdir('dist'):
            shutil.rmtree('dist')
        if isdir(name + '.egg-info'):
            shutil.rmtree(name + '.egg-info')
        download_manta(logger, only_clean=True)
        download_blast_binaries(logger, only_clean=True)
        download_blastdb(logger, only_clean=True)
        if qconfig.platform_name != 'macosx':
            download_augustus(logger, only_clean=True)
            download_all_db(logger, only_clean=True)
        logger.info('Done.')
        sys.exit()


if cmd_in(['test']):
    ret_code = os.system('quast.py --test')
    sys.exit(ret_code)


def write_version_py():
    version_py = os.path.join(os.path.dirname(__file__), quast_package, 'version.py')

    with open('VERSION.txt') as f:
        v = f.read().strip().split('\n')[0]
    try:
        import subprocess
        git_revision = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'],
                                               stderr=open(os.devnull, 'w')).rstrip()
    except:
        git_revision = ''
        pass

    if not isinstance(git_revision, str):
        git_revision = git_revision.decode('utf-8')
    with open(version_py, 'w') as f:
        f.write((
            '# Do not edit this file, pipeline versioning is governed by git tags\n'+
                    '__version__ = \'' + v + '\'\n' +
                    '__git_revision__ = \'%s\'' % git_revision))
    return v

version = write_version_py()


if cmd_in(['tag']):
    cmdl = 'git tag -a %s -m "Version %s" && git push --tags' % (version, version)
    os.system(cmdl)
    sys.exit()


if cmd_in(['publish']):
    cmdl = 'git clean -dfx && python setup.py sdist upload'
    os.system(cmdl)
    sys.exit()


def find_package_files(dirpath, package=quast_package):
    paths = []
    for (path, dirs, fnames) in os.walk(join(package, dirpath)):
        for fname in fnames:
            paths.append(qutils.relpath(join(path, fname), package))
    return paths


install_full = False
if cmd_in(['install_full']):
    install_full = True
    args2 = []
    for a_ in args:
        if a_ == 'install_full':
            args2.append('install')
        else:
            args2.append(a_)
    args = args2

modules_failed_to_install = []
if cmd_in(['install', 'develop', 'build', 'build_ext']):
    try:
        import matplotlib
    except ImportError:
        try:
            pip.main(['install', 'matplotlib'])
        except:
            logger.warning('Cannot install matplotlib. Static plots will not be drawn (however, HTML will be)')

    logger.info('* Compiling aligner *')
    if not compile_aligner(logger):
        modules_failed_to_install.append('Contigs aligners for reference-based evaluation (affects -R and many other options)')
    logger.info('* Compiling gnuplot *')
    if not compile_gnuplot(logger):
        logger.warning('Cannot compile gnuplot. MUMmer plots will not be drawn')
    logger.info('* Compiling Glimmer *')
    if not compile_glimmer(logger):
        modules_failed_to_install.append('Glimmer gene-finding tool (affects --glimmer option)')
    logger.info('* Compiling read analysis tools *')
    if not compile_reads_analyzer_tools(logger):
        modules_failed_to_install.append('Read analysis tools (affects -1/--reads1 and -2/--reads2 options)')
    if install_full:
        logger.info('* Downloading Manta *')
        if not download_manta(logger):
            modules_failed_to_install.append('Manta (affects -1/--reads1 and -2/--reads2 options)')
        logger.info('* Downloading BLAST *')
        if not download_blast_binaries(logger):
            modules_failed_to_install.append('BLAST (affects metaquast.py in without references mode and --find-conserved-genes option)')
        logger.info('* Downloading SILVA 16S rRNA gene database *')
        if not download_blastdb(logger):
            modules_failed_to_install.append('SILVA 16S rRNA gene database (affects metaquast.py in without references mode)')
        if qconfig.platform_name != 'macosx':
            logger.info('* Downloading and compiling Augustus *')
            if not download_augustus(logger):
                modules_failed_to_install.append('Augustus (affects --find-conserved-genes option)')
            logger.info('* Downloading BUSCO databases *')
            if not download_all_db(logger):
                modules_failed_to_install.append('BUSCO databases (affects --find-conserved-genes option)')
        else:
            logger.notice('* BUSCO dependecies will not be installed (unavailable in OS X) *')
        logger.info('* Compiling GAGE *')
        if not compile_gage():
            modules_failed_to_install.append('GAGE scripts (affects --gage option [deprecated, will be removed soon])')
    logger.info('')


if qconfig.platform_name == 'macosx':
    sambamba_files = [join('sambamba', 'sambamba_osx')]
else:
    sambamba_files = [join('sambamba', 'sambamba_linux')]

nucmer_files = find_package_files('MUMmer')
bwa_files = [
    join('bwa', fp) for fp in os.listdir(join(quast_package, 'bwa'))
    if isfile(join(quast_package, 'bwa', fp)) and fp.startswith('bwa')]
full_install_tools = (
    find_package_files('manta') +
    find_package_files('blast') +
    [join(quast_package, 'busco', 'hmmsearch')]
)

setup(
    name=name,
    version=version,
    author='Alexey Gurevich, Vladislav Saveliev, Alla Mikheenko, and others',
    author_email='quast.support@bioinf.spbau.ru',
    description='Genome assembly evaluation tool',
    long_description='''QUAST evaluates genome assemblies.
It works both with and without reference genomes.
The tool accepts multiple assemblies, thus is suitable for comparison.''',
    keywords=['bioinformatics', 'genome assembly', 'metagenome assembly', 'visualization'],
    url='http://quast.sf.net',
    download_url='https://sourceforge.net/projects/quast/files',
    platforms=['Linux', 'OS X'],
    license='GPLv2',

    packages=find_packages(),
    package_data={
        quast_package:
            find_package_files('html_saver') +
            nucmer_files +
            find_package_files('genemark/' + qconfig.platform_name) +
            find_package_files('genemark-es/' + qconfig.platform_name) +
            find_package_files('genemark-es/lib') +
            find_package_files('glimmer') +
            find_package_files('gage') +
            bwa_files +
            ['bedtools/bin/*'] +
            sambamba_files +
           (full_install_tools if install_full else [])
    },
    include_package_data=True,
    zip_safe=False,
    scripts=['quast.py', 'metaquast.py', 'icarus.py'],
    install_requires=[
        'joblib',
        'simplejson',
    ],
    classifiers=[
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: JavaScript',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Scientific/Engineering :: Visualization',
    ],
    script_args=args,
)


if cmd_in(['install']):
    not_installed_message = ''
    if modules_failed_to_install:
        not_installed_message = 'WARNING: some modules were not installed properly and\n' \
                                'QUAST functionality will be restricted!\n' \
                                'The full list of malformed modules and affected options:\n'
        not_installed_message += "\n".join(map(lambda x: " * " + x, modules_failed_to_install))
        not_installed_message += "\n\n"

    if not install_full:
        logger.info('''
----------------------------------------------
QUAST version %s installation complete.

%sPlease run  ./setup.py test   to verify installation.

For help in running QUAST, please see the documentation available
at quast.sf.net/manual.html, or run quast.py --help

Usage:
$ quast.py test_data/contigs_1.fasta \\
           test_data/contigs_2.fasta \\
        -R test_data/reference.fasta.gz \\
        -G test_data/genes.txt \\
        -o quast_test_output
----------------------------------------------''' % (str(version), not_installed_message))

    else:
        logger.info('''
----------------------------------------------
QUAST version %s installation complete.

The full package is installed, with the features for reference
sequence detection in MetaQUAST, and structural variant detection
for misassembly events refinement.

%sPlease run  ./setup.py test   to verify installation.

For help in running QUAST, please see the documentation available
at quast.sf.net/manual.html, or run quast.py --help

Usage:
$ quast.py test_data/contigs_1.fasta \\
           test_data/contigs_2.fasta \\
        -R test_data/reference.fasta.gz \\
        -G test_data/genes.txt \\
        -1 test_data/reads1.fastq.gz -2 test_data/reads2.fastq.gz \\
        -o quast_test_output
----------------------------------------------''' % (str(version), not_installed_message))
