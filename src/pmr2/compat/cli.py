import json

from argparse import ArgumentParser
from cStringIO import StringIO
from inspect import getargspec
from lxml import etree
from os.path import join

from cellml.api.pmr2.utility import CellMLAPIUtility
from cellml.pmr2.cmeta import Cmeta

# citation

def citation_cellml(input_path):
    with open(input_path) as fd:
        metadata = Cmeta(fd)
    return metadata.get_license()


citation_extract = {
    'cellml': citation_cellml,
}


def citation(input_path, output_dir, license_uri, file_format=None):
    extracted = citation_extract.get(file_format, lambda _: None)(input_path)
    if extracted:
        license_uri = extracted
    output_file = join(output_dir, 'license.txt')
    with open(output_file, 'w') as fd:
        fd.write(license_uri)


# codegen

codegen_fileext = {
    'Python': 'py',
    'C_IDA': 'c',
    'C': 'c',
    'F77': 'f77',
    'MATLAB': 'm',
}

def codegen(input_path, output_dir):
    cu = CellMLAPIUtility()
    model = cu.model_loader.loadFromURL(input_path)
    for k, v in cu.exportCeleds(model).items():
        output_file = join(output_dir, 'code.%s.%s' % (k, codegen_fileext[k]))
        with open(output_file, 'w') as fd:
            fd.write(v)


# cmeta

def cmeta(input_path, output_dir):
    import re
    re_date = re.compile('^[0-9]{4}(-[0-9]{2}){0,2}')

    def generate_citation():
        ids = metadata.get_cmetaid()
        if not ids:
            # got no cmetaid, assuming no CellML metadata present.
            return

        citation = metadata.get_citation(ids[0])
        if not citation:
            # no citation, do nothing.
            return

        result['citation_id'] = citation[0]['citation_id']
        # more than just journal
        result['citation_bibliographicCitation'] = citation[0]['journal']
        result['citation_title'] = citation[0]['title']

        # XXX ad-hoc sanity checking
        issued = citation[0]['issued']
        if isinstance(issued, basestring) and re_date.search(issued):
            result['citation_issued'] = issued
        else:
            result['citation_issued'] = u''

        authors = []
        if not citation[0]['creator']:
            # no authors, we do not need the last field.
            return

        for c in citation[0]['creator']:
            family = c['family']
            given = c['given']
            if c['other']:
                other = ' '.join(c['other'])
            else:
                other = ''
            fn = (family, given, other)
            authors.append(fn)

        result['citation_authors'] = authors

    def generate_keywords():
        result['keywords'] = metadata.get_keywords()

    def generate_model_title():
        model_title = metadata.get_dc_title(node='')
        if model_title:
            result['model_title'] = model_title[0]

    def generate_model_authorship():
        dcvc = metadata.get_dc_vcard_info(node='')
        if not dcvc:
            return
        # using only first one
        info = dcvc[0]
        result['model_author'] = '%s %s' % (info['given'], info['family'])
        result['model_author_org'] = \
            '%s, %s' % (info['orgunit'], info['orgname'])

    result = {}
    with open(input_path) as fd:
        metadata = Cmeta(fd)

    generate_citation()
    generate_keywords()
    generate_model_title()
    generate_model_authorship()

    output_file = join(output_dir, 'cmeta.json')
    with open(output_file, 'w') as fd:
        json.dump(result, fd)


# maths

def maths(input_path, output_dir):
    from cellml.pmr2.annotator import mathmlc2p_xslt
    def mathc2p(s):
        r = StringIO()
        t = etree.parse(StringIO(s))
        t.xslt(mathmlc2p_xslt).write(r)
        return r.getvalue()

    cu = CellMLAPIUtility()
    model = cu.model_loader.loadFromURL(input_path)
    # model = cu.loadModel(target, loader=pmr_loader)
    maths = cu.extractMaths(model)
    maths = [(k, [mathc2p(m) for m in v]) for k, v in maths]
    output_file = join(output_dir, 'math.json')
    with open(output_file, 'w') as fd:
        json.dump(maths, fd)


# docgen

def tmpdoc(input_path, output_dir):
    from pmr2.processor.legacy.transforms import tmpdoc2html
    with open(input_path) as inc:
        output = tmpdoc2html(inc)
        output_file = join(output_dir, 'index.html')
        with open(output_file, 'w') as fd:
            fd.write(output.getvalue())

def htmldoc(input_path, output_dir):
    with open(input_path) as inc:
        output_file = join(output_dir, 'index.html')
        with open(output_file, 'w') as fd:
            fd.write(inc.read())

docs = [
    (htmldoc, 'HTML Documentation'),
    (tmpdoc, 'CellML legacy tmpdoc'),
]

docs_lookup = {fn.__name__: fn for fn, _ in docs}

def docgen(doctype, input_path, output_dir):
    docs_lookup[doctype](input_path, output_dir)

# set up commands

cmd_fns = [
    (citation, 'Citation'),
    (cmeta, 'CellML metadata'),
    (codegen, 'CellML codegen'),
    (docgen, 'CellML docgen'),
    (maths, 'CellML math'),
]

def generate_cmd_parser(cmd_fns):
    commands = {}
    argparser = ArgumentParser()
    ap_grp = argparser.add_subparsers(dest='cmd', metavar='<command>')

    for cmd_fn, help_text in cmd_fns:
        commands[cmd_fn.__name__] = cmd_fn
        sub_ap = ap_grp.add_parser(cmd_fn.__name__, help=help_text)
        argspec = getargspec(cmd_fn)
        defaults = dict(zip(reversed(argspec.args), argspec.defaults or ()))
        for arg in argspec.args:
            sub_ap.add_argument(
                '--' + arg.replace('_', '-'),
                action='store',
                required=arg not in defaults,
                default=defaults.get(arg),
            )

    return commands, argparser


def main():
    commands, argparser = generate_cmd_parser(cmd_fns)
    kwargs = vars(argparser.parse_args())
    cmd_key = kwargs.pop('cmd')
    commands[cmd_key](**kwargs)
