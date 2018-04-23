import requests
import json
import pysolr
from dictionary.matcher import Dictionary_Matcher

#
# Named Entity Linking, Disambiguation and Normalization by Named Entities in Solr search index
#
# Links plain text names/labels to ID/URI and normalize alias or alternate label to preferred label
#
# Queries are entity names as strings and/or plain text from which named entities will be extracted and can be scored by the context.
# Specification: https://github.com/OpenRefine/OpenRefine/wiki/Reconciliation-Service-API#query-request
#
# If no entity queries the entities will be extracted from the (con)text
#
# Returns Named Entities in Open Refine Reconciliation Service result format
# Specification: https://github.com/OpenRefine/OpenRefine/wiki/Reconciliation-Service-API#query-response

class Entity_Linker(object):

	solr = 'http://localhost:8983/solr/'
	solr_core = 'core1-dictionary'
	
	fields = ['id', 'label_ss', 'preferred_label_s', 'skos_prefLabel_ss', 'skos_altLabel_ss', 'skos_hiddenLabel_ss']

	def dictionary_matches(self, text):
		
		queries = {}
		dictionary_matcher = Dictionary_Matcher()
		matches = dictionary_matcher.matches(text=text)
		for dict in matches:
			for match in matches[dict]:
				queries[match] = {'query': match}

		return queries


	def entities(self, queries=None, language=None, normalized_label_languages=['en'], text = None, limit=10000):

		normalized_entities = {}

		# if no entities queries, match entities from dictionary of labels from thesaurus, ontologies, databases and lists
		if not queries:
			queries = self.dictionary_matches(text=text)

		headers = {'content-type' : 'application/json'}

		search_result_fields = self.fields
		search_result_fields.append("score")

		for query in queries:

			params = {
				'wt': 'json',
				'defType': 'edismax',
				'qf': ['label_ss', 'preferred_label_s^10', 'skos_prefLabel_ss^10', 'skos_altLabel_ss','skos_hiddenLabel_ss'],
				'fl': search_result_fields,
				'q': "\"" + queries[query]['query'] + "\"",
			}

			if 'limit' in queries[query]:
				params['rows'] = queries[query]['limit']
			else:
				params['rows'] = limit
				
			r = requests.get(self.solr + self.solr_core + '/select', params=params, headers=headers)
			search_results = r.json()

			normalized_entities[query]={}
			normalized_entities[query]['result'] = []

			results = []

			for search_result in search_results['response']['docs']:

				label = None

				if 'preferred_label_s' in search_result:
					label = search_result['preferred_label_s']

				if not label:
					if 'skos_prefLabel_ss' in search_result:
						label = search_result['skos_prefLabel_ss'][0]

				if not label:
					if 'label_ss' in search_result:
						label = search_result['label_ss'][0]

				if not label:
					if 'skos_altLabel_ss' in search_result:
						label = search_result['skos_altLabel_ss'][0]

				if not label:
					label = search_result['id']

				match = False
				for field in self.fields:
					if field in search_result:

						values = search_result[field]
						if not isinstance(values, list):
							values = [values]

						for value in values:
							if str(value).lower() == queries[query]['query'].lower():
								match = True
				
				result = {
					'id': search_result['id'],
					'name': label,
					'score': search_result['score'],
					'match': match,
				}
				
				results.append(result)
				
			normalized_entities[query]['result'] = results

		return normalized_entities
