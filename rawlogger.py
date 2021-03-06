# -*- coding: utf-8 -*-
import irc3
import os, logging, codecs, pytz
from tzlocal import get_localzone
from datetime import datetime
from irc3.utils import as_list
__doc__ = '''
=============================================
:mod:`rawlogger.py` Channel raw logger plugin
=============================================

Log channels in raw format

..
	>>> from irc3.testing import IrcBot

Usage::

	>>> bot = IrcBot(**{
	...	 'rawlogger': {
	...		 'handler': 'rawlogger.file_handler',
	...	 },
	... })
	>>> bot.include('rawlogger')


Available handlers:

.. autoclass:: file_handler
'''


class file_handler:
	"""Write logs to file in ~/.irc3/logs
	"""

	def __init__(self, bot):
		config = {
			'filename': '~/.irc3/logs/{host}/{channel}-{date:%Y-%m-%d}.raw.log',
			'formatter': '{date:%Y-%m-%dT%H:%M:%S.%f%z} {raw}',
		}
		config.update(bot.config.get(__name__, {}))
		self.filename = config['filename']
		self.encoding = bot.encoding
		self.formatter = config['formatter']

	def __call__(self, event):
		filename = self.filename.format(**event)
		if not os.path.isfile(filename):
			dirname = os.path.dirname(filename)
			if not os.path.isdir(dirname):  # pragma: no cover
				os.makedirs(dirname, exist_ok=True)
		with codecs.open(filename, 'a+', self.encoding) as fd:
			fd.write(self.formatter.format(**event) + '\r\n')


@irc3.plugin
class RawLogger:
	"""Logger plugin. Use the :class:~file_handler handler by default
	"""

	def message_filtered(self, message):
		if not self.message_filters:
			return False

		for message_filter in self.message_filters:
			if message_filter in message:
				return False

		# self.bot.log.debug('*** FILTERED ***')
		return True

	def __init__(self, bot):
		self.bot = bot
		self.config = bot.config.get(__name__, {})

		handler = irc3.utils.maybedotted(self.config.get('handler', file_handler))
		self.bot.log.debug('Handler: %s', handler.__name__)
		self.handler = handler(bot)

		self.message_filters = []
		#self.bot.log.info('Filters:')
		for message_filter in as_list(self.config.get('filters')):
			self.message_filters.append(message_filter)
			#self.bot.log.info(message_filter)

	def process(self, **kwargs):
		if self.message_filtered(kwargs['raw']):
			return

		kw = dict(host=self.bot.config.host, channel='#%s' % kwargs['channelname'], date=datetime.now(get_localzone()), **kwargs)
		self.handler(kw)

	@irc3.event('(?P<pre>(@\S+ )?:\S+ \S+ #)(?P<channelname>\S+)(?P<post>.*)')
	def on_input(self, pre, channelname, post, **kwargs):
		raw = pre + channelname + post
		self.process(channelname=channelname, raw=raw, **kwargs)

	@irc3.event('(?P<pre>(@\S+ )?\S+ #)(?P<channelname>\S+)(?P<post>.*)', iotype='out')
	def on_output(self, pre, channelname, post, **kwargs):
		raw = pre + channelname + post
		self.process(channelname=channelname, raw=raw, **kwargs)
