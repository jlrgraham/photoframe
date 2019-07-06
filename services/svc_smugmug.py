# This file is part of photoframe (https://github.com/mrworf/photoframe).
#
# photoframe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# photoframe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with photoframe.  If not, see <http://www.gnu.org/licenses/>.

from base import BaseService
import os
import re
import logging
import feedparser

from modules.helper import helper


class SmugMug(BaseService):
	SERVICE_NAME = 'SmugMug'
	SERVICE_ID   = 5

	def __init__(self, configDir, id, name):
		BaseService.__init__(self, configDir, id, name, needConfig=False, needOAuth=False)

		self.brokenUrls = []


	def helpKeywords(self):
		return 'Each item is a URL for a SmugMug gallery feed.'


	def removeKeywords(self, index):
		url = self.getKeywords()[index]
		result = BaseService.removeKeywords(self, index)

		if result and url in self.brokenUrls:
			self.brokenUrls.remove(url)

		return result


	def hasKeywordSourceUrl(self):
		return True


	def getKeywordSourceUrl(self, index):
		keys = self.getKeywords()

		if index < 0 or index >= len(keys):
			return 'Out of range, index = %d' % index

		return keys[index]


	def validateKeywords(self, keywords):
		# Catches most invalid URLs
		if not helper.isValidUrl(keywords):
			return {'error': 'URL appears to be invalid', 'keywords': keywords}

		return BaseService.validateKeywords(self, keywords)


	def memoryForget(self, keywords=None, forgetHistory=False):
		# give broken URLs another try (server may have been temporarily unavailable)
		self.brokenUrls = []

		return BaseService.memoryForget(self, keywords=keywords, forgetHistory=forgetHistory)


	def getUrlFilename(self, url):
		return url.rsplit("/", 1)[-1]


	def selectImageFromAlbum(self, destinationDir, supportedMimeTypes, displaySize, randomize, retry=1):
		result = BaseService.selectImageFromAlbum(self, destinationDir, supportedMimeTypes, displaySize, randomize)
		if result is None:
			return None

		# catch broken urls
		if result["error"] is not None and result["source"] is not None:
			logging.warning("broken url detected. You should remove '.../%s' from keywords" % (self.getUrlFilename(result["source"])))
		# catch unsupported mimetypes (can only be done after downloading the image)
		elif result["error"] is None and result["mimetype"] not in supportedMimeTypes:
			logging.warning("unsupported mimetype '%s'. You should remove '.../%s' from keywords" % (result["mimetype"], self.getUrlFilename(result["source"])))
		else:
			return result

		# track broken urls / unsupported mimetypes and display warning message on web interface
		self.brokenUrls.append(result["source"])
		# retry (with another image)
		if retry > 0:
			return self.selectImageFromAlbum(destinationDir, supportedMimeTypes, displaySize, randomize, retry=retry-1)

		return {
			'id': None,
			'mimetype': None,
			'error': '%s uses broken urls / unsupported images!' % self.SERVICE_NAME,
			'source': None
		}


	def getImagesFor(self, url):
		if url in self.brokenUrls:
			return []

		images = []

		feed = feedparser.parse(url)
		for entry in feed['entries']:
			url = entry['id'].replace('-Th.', '-X5.').replace('/Th/', '/X5/')

			image = {
				"id": self.hashString(entry['id']),
				"size": None,
				"url": url,
				"mimetype": None,
				"source": url,
				"filename": entry['id'].split('/')[-1].replace('-Th.', '.'),
			}
			images.append(image)

		return images


	def resetToLastAlbum(self):
		self.resetIndices()
