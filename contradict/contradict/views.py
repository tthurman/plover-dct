from django.shortcuts import render
from django.http import HttpResponseRedirect
from .forms import DictionaryUploadForm
from .settings import MEDIA_ROOT
import os
import random
from contradict.formats.DctDict import DctDict
from contradict.formats.JsonDict import JsonDict
from contradict.formats.RtfDict import RtfDict

# this would be better done with introspection
FORMATS = [
		DctDict,
		RtfDict,
		JsonDict,
	]

NORMALISED_FORMAT = JsonDict

def _random_filename():
	return ''.join(
		[hex(random.randrange(16))[2]
			for i in range(10)])

def _filestore_filename(request):
	return os.path.join(MEDIA_ROOT,
		request.session['our_id'])

def _store_dictionary(f, request):

	dest = open(_filestore_filename(request),
		'wb')

        for chunk in f.chunks():
        	dest.write(chunk)

def _find_format(request):
	fh = open(_filestore_filename(request), 'rb')

	for dformat in FORMATS:
		if dformat.can_handle(fh):
			fh.close()
			return dformat

	fh.close()
	return None

def _normalise_upload(dformat, request):
	filename = _filestore_filename(request)
	temp_filename = filename+'.1'

	contents = dformat.load_from_file(filename)
	NORMALISED_FORMAT.save_to_file(temp_filename, contents)

def _handle_upload(request):
	uploaded_file = request.FILES.get('dictionary')
	file_id = _random_filename()

	request.session['our_id'] = file_id
	request.session['their_name'] = uploaded_file.name
	request.session['dict_size'] = uploaded_file.size

	_store_dictionary(uploaded_file, request)

	# now, what kind of dictionary do we have?
	dformat = _find_format(request)

	if dformat is None:
		request.session['unknown_format'] = True
		del request.session['our_id']
		return

	request.session['dict_format'] = dformat.title()

	try:
		_normalise_upload(dformat, request)
	except ValueError, ve:
		request.session['general_error'] = ve.message
		del request.session['our_id']

def _download_formats(basename):

	return [(
		basename+'.'+x.keyword(),
		x.title(),
		x.keyword(),
		) for x in FORMATS if x.can_save_to_file()]

def root_view(request):

	render_vars = {}

	# first off-- are they uploading?

	if request.method=='POST':
		form = DictionaryUploadForm(request.POST,
			request.FILES)

		if form.is_valid():

			# yes, they're uploading.

			_handle_upload(request)
			render_vars['uploaded'] = True

	# now, either they have a file or they don't.
	# if they do, show some information about it.
	# if they don't, they need the upload form.

	if request.session.has_key('our_id') and \
		not os.path.exists(_filestore_filename(request)):

			# they HAD a file; we deleted it

			render_vars['deleted'] = request.session['their_name']

			request.session.clear()

	if request.session.has_key('our_id'):

		# they do have a file.
		# check their file has a name!

		their_name = request.session['their_name']

		if not their_name:
			# shouldn't happen, but just in case...
			their_name = request.session['their_name'] = 'dictionary'

		# right, now we have to adjust download_formats
		# so that the links are to "whatever.json" etc.

		if '.' in their_name:
			name_without_extension = their_name[:their_name.rindex('.')]
		else:
			name_without_extension = their_name

		
		request.session['download_formats'] = _download_formats(name_without_extension)
	else:

		# they don't have a file;
		# let them upload one

		render_vars['form'] = DictionaryUploadForm()

	# Copy anything remaining in request.session (for which
	# we don't already have a value) into render_vars.

	for (field, value) in request.session.items():
		if not render_vars.has_key(field):
			render_vars[field] = value

	return render(request, 'root_page.html', render_vars)

def download_view(request, filename):

	for (name, title, keyword) in request.session['download_formats']:
		if name==filename:
			raise ValueError('Got '+keyword)

	raise ValueError('not on offer')

def logout_view(request):
	request.session.clear()
	return HttpResponseRedirect('/')
