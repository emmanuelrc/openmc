import copy
import os
from xml.etree import ElementTree as ET

from openmc import Mesh, Filter, Trigger, Nuclide
from openmc.clean_xml import *
from openmc.checkvalue import *


# "Static" variable for auto-generated Tally IDs
AUTO_TALLY_ID = 10000


def reset_auto_tally_id():
    global AUTO_TALLY_ID
    AUTO_TALLY_ID = 10000


class Tally(object):

    def __init__(self, tally_id=None, name=''):

        # Initialize Tally class attributes
        self.id = tally_id
        self.name = name
        self._filters = []
        self._nuclides = []
        self._scores = []
        self._estimator = None
        self._triggers = []

        self._num_score_bins = 0
        self._num_realizations = 0

        self._sum = None
        self._sum_sq = None
        self._mean = None
        self._std_dev = None


    def __deepcopy__(self, memo):

        existing = memo.get(id(self))

        # If this is the first time we have tried to copy this object, create a copy
        if existing is None:

            clone = type(self).__new__(type(self))
            clone._id = self._id
            clone._name = self._name
            clone._estimator = self._estimator
            clone._num_score_bins = self._num_score_bins
            clone._num_realizations = self._num_realizations
            clone._sum = copy.deepcopy(self._sum, memo)
            clone._sum_sq = copy.deepcopy(self._sum_sq, memo)
            clone._mean = copy.deepcopy(self._mean, memo)
            clone._std_dev = copy.deepcopy(self._std_dev, memo)

            clone._filters = []
            for filter in self._filters:
              clone.add_filter(copy.deepcopy(filter, memo))

            clone._nuclides = []
            for nuclide in self._nuclides:
              clone.add_nuclide(copy.deepcopy(nuclide, memo))

            clone._scores = []
            for score in self._scores:
              clone.add_score(score)

            clone._triggers = []
            for trigger in self._triggers:
              clone.add_trigger(trigger)

            memo[id(self)] = clone

            return clone

        # If this object has been copied before, return the first copy made
        else:
            return existing


    def __eq__(self, tally2):

        # Check all filters
        for filter in self._filters:
            if not filter in tally2._filters:
                return False

        # Check all nuclides
        for nuclide in self._nuclides:
            if not nuclide in tally2._nuclides:
                return False

        # Check all scores
        for score in self._scores:
            if not score in tally2._scores:
                return False

        if self._estimator != tally2._estimator:
            return False

        return True


    def __hash__(self):
        hashable = []

        for filter in self._filters:
            hashable.append((filter._type, tuple(filter._bins)))

        for nuclide in self._nuclides:
            hashable.append(nuclide._name)

        for score in self._scores:
            hashable.append(score)

        hashable.append(self._estimator)
        hashable.append(self._name)

        return hash(tuple(hashable))


    def __add__(self, other):

        # FIXME: Error checking: must check that results has been
        # set and that # bins is the same

        new_tally = Tally()
        new_tally._mean = self._mean + other._mean
        new_tally._std_dev = np.sqrt(self._std_dev**2 + other._std_dev**2)


    @property
    def id(self):
        return self._id


    @property
    def name(self):
        return self._name


    @property
    def filters(self):
        return self._filters


    @property
    def num_filters(self):
        return len(self._filters)


    @property
    def nuclides(self):
        return self._nuclides


    @property
    def num_nuclides(self):
        return len(self._nuclides)


    @property
    def scores(self):
        return self._scores


    @property
    def num_scores(self):
        return len(self._scores)


    @property
    def num_score_bins(self):
        return self._num_score_bins


    @property
    def num_filter_bins(self):

        num_bins = 1

        for filter in self._filters:
            num_bins *= filter.num_bins

        return num_bins


    @property
    def num_bins(self):
        num_bins = self.num_filter_bins
        num_bins *= self.num_nuclides
        num_bins *= self.num_score_bins
        return num_bins


    @property
    def estimator(self):
        return self._estimator


    @property
    def triggers(self):
        return self._triggers


    @property
    def num_realizations(self):
        return self._num_realizations


    @property
    def sum(self):
        return self._sum


    @property
    def sum_sq(self):
        return self._sum_sq


    @property
    def mean(self):
        return self._mean


    @property
    def std_dev(self):
        return self._std_dev


    @estimator.setter
    def estimator(self, estimator):

        if not estimator in ['analog', 'tracklength']:
            msg = 'Unable to set the estimator for Tally ID={0} to {1} since ' \
                  'it is not a valid estimator type'.format(self._id, estimator)
            raise ValueError(msg)

        self._estimator = estimator


    def add_trigger(self, trigger):

        if not isinstance(trigger, Trigger):
            msg = 'Unable to add a tally trigger for  for Tally ID={0} to ' \
                  '{1} since it is not a valid estimator type'.format(trigger)
            raise ValueError(msg)

        self._triggers.append(trigger)


    @id.setter
    def id(self, tally_id):

        if tally_id is None:
            global AUTO_TALLY_ID
            self._id = AUTO_TALLY_ID
            AUTO_TALLY_ID += 1

        # Check that the ID is an integer and wasn't already used
        elif not is_integer(tally_id):
            msg = 'Unable to set a non-integer Tally ID {0}'.format(tally_id)
            raise ValueError(msg)

        elif tally_id < 0:
            msg = 'Unable to set Tally ID to {0} since it must be a ' \
                  'non-negative integer'.format(tally_id)
            raise ValueError(msg)

        else:
            self._id = tally_id


    @name.setter
    def name(self, name):

        if not is_string(name):
            msg = 'Unable to set name for Tally ID={0} with a non-string ' \
                  'value {1}'.format(self._id, name)
            raise ValueError(msg)

        else:
            self._name = name


    def add_filter(self, filter):

        global filters

        if not isinstance(filter, Filter):
            msg = 'Unable to add Filter {0} to Tally ID={1} since it is not ' \
                  'a Filter object'.format(filter, self._id)
            raise ValueError(msg)

        self._filters.append(filter)


    def add_nuclide(self, nuclide):
        self._nuclides.append(nuclide)


    def add_score(self, score):

        if not is_string(score):
            msg = 'Unable to add score {0} to Tally ID={1} since it is not a ' \
                  'string'.format(score, self._id)
            raise ValueError(msg)

        # If the score is already in the Tally, don't add it again
        if score in self._scores:
            return
        else:
            self._scores.append(score)


    @num_score_bins.setter
    def num_score_bins(self, num_score_bins):
        self._num_score_bins = num_score_bins


    @num_realizations.setter
    def num_realizations(self, num_realizations):

        if not is_integer(num_realizations):
            msg = 'Unable to set the number of realizations to {0} for ' \
                  'Tally ID={1} since it is not an ' \
                  'integer'.format(num_realizations)
            raise ValueError(msg)

        elif num_realizations < 0:
            msg = 'Unable to set the number of realizations to {0} for ' \
                  'Tally ID={1} since it is a negative ' \
                  'value'.format(num_realizations)
            raise ValueError(msg)

        self._num_realizations = num_realizations


    def set_results(self, sum, sum_sq):

        if not isinstance(sum, (tuple, list, np.ndarray)):
            msg = 'Unable to set the sum to {0}for Tally ID={1} since ' \
                  'it is not a Python tuple/list or NumPy ' \
                  'array'.format(sum, self._id)
            raise ValueError(msg)

        if not isinstance(sum_sq, (tuple, list, np.ndarray)):
            msg = 'Unable to set the sum to {0}for Tally ID={1} since ' \
                  'it is not a Python tuple/list or NumPy ' \
                  'array'.format(sum_sq, self._id)
            raise ValueError(msg)

        self._sum = sum
        self._sum_sq = sum_sq


    def remove_score(self, score):

        if not score in self._scores:
            msg = 'Unable to remove score {0} from Tally ID={1} since the ' \
                  'Tally does not contain this score'.format(score, self._id)
            ValueError(msg)

        self._scores.remove(score)


    def remove_filter(self, filter):

        if not filter in self._filters:
            msg = 'Unable to remove filter {0} from Tally ID={1} since the ' \
                  'Tally does not contain this filter'.format(filter, self._id)
            ValueError(msg)

        self._filters.remove(filter)


    def remove_nuclide(self, nuclide):

        if not nuclide in self._nuclides:
            msg = 'Unable to remove nuclide {0} from Tally ID={1} since the ' \
                  'Tally does not contain this nuclide'.format(nuclide, self._id)
            ValueError(msg)

        self._nuclides.remove(nuclide)


    def compute_std_dev(self, t_value=1.0):

        # Calculate sample mean and standard deviation
        self._mean = self._sum / self._num_realizations
        self._std_dev = np.sqrt((self._sum_sq / self._num_realizations - \
                                 self._mean**2) / (self._num_realizations - 1))
        self._std_dev *= t_value


    def __repr__(self):

        string = 'Tally\n'
        string += '{0: <16}{1}{2}\n'.format('\tID', '=\t', self._id)
        string += '{0: <16}{1}{2}\n'.format('\tName', '=\t', self._name)

        string += '{0: <16}\n'.format('\tFilters')

        for filter in self._filters:
            string += '{0: <16}\t\t{1}\t{2}\n'.format('', filter._type,
                                                          filter._bins)

        string += '{0: <16}{1}'.format('\tNuclides', '=\t')

        for nuclide in self._nuclides:
            if isinstance(nuclide, Nuclide):
                string += '{0} '.format(nuclide._name)
            else:
                string += '{0} '.format(nuclide)

        string += '\n'

        string += '{0: <16}{1}{2}\n'.format('\tScores', '=\t', self._scores)
        string += '{0: <16}{1}{2}\n'.format('\tEstimator', '=\t', self._estimator)

        return string


    def can_merge(self, tally):

        if not isinstance(tally, Tally):
            return False

        # Must have same estimator
        if self._estimator != tally._estimator:
            return False

        # Must have same nuclides
        if len(self._nuclides) != len(tally._nuclides):
            return False

        for nuclide in self._nuclides:
            if not nuclide in tally._nuclides:
                return False

        # Must have same or mergeable filters
        if len(self._filters) != len(tally._filters):
            return False

        # Look to see if all filters are the same, or one or more can be merged
        for filter1 in self._filters:
            mergeable_filter = False

            for filter2 in tally._filters:
                if filter1 == filter2 or filter1.can_merge(filter2):
                    mergeable_filter = True
                    break

            # If no mergeable filter was found, the tallies are not mergable
            if not mergeable_filter:
                return False

        # Tallies are mergeable if all conditional checks passed
        return True


    def merge(self, tally):

        if not self.can_merge(tally):
            msg = 'Unable to merge tally ID={0} with {1}'.format(tally.id, self.id)
            raise ValueError(msg)

        # Create deep copy of tally to return as merged tally
        merged_tally = copy.deepcopy(self)

        # Differentiate Tally with a new auto-generated Tally ID
        merged_tally.id = None

        # Merge filters
        for i, filter1 in enumerate(merged_tally._filters):
            for filter2 in tally._filters:
                if filter1 != filter2 and filter1.can_merge(filter2):
                    merged_filter = filter1.merge(filter2)
                    merged_tally._filters[i] = merged_filter
                    break

        # Add scores from second tally to merged tally
        for score in tally._scores:
            merged_tally.add_score(score)

        # Add triggers from second tally to merged tally
        for trigger in tally._triggers:
            merged_tally.add_trigger(trigger)

        return merged_tally


    def get_tally_xml(self):

        element = ET.Element("tally")

        # Tally ID
        element.set("id", str(self._id))

        # Optional Tally name
        if self._name != '':
            element.set("name", self._name)

        # Optional Tally filters
        for filter in self._filters:

            subelement = ET.SubElement(element, "filter")
            subelement.set("type", str(filter._type))

            if not filter._bins is None:

                bins = ''
                for bin in filter._bins:
                    bins += '{0} '.format(bin)

                subelement.set("bins", bins.rstrip(' '))

        # Optional Nuclides
        if len(self._nuclides) > 0:

            nuclides = ''
            for nuclide in self._nuclides:
                if isinstance(nuclide, Nuclide):
                    nuclides += '{0} '.format(nuclide._name)
                else:
                    nuclides += '{0} '.format(nuclide)

            subelement = ET.SubElement(element, "nuclides")
            subelement.text = nuclides.rstrip(' ')

        # Scores
        if len(self._scores) == 0:
            msg = 'Unable to get XML for Tally ID={0} since it does not ' \
                  'contain any scores'.format(self._id)
            raise ValueError(msg)

        else:

            scores = ''
            for score in self._scores:
                scores += '{0} '.format(score)

            subelement = ET.SubElement(element,    "scores")
            subelement.text = scores.rstrip(' ')

        # Tally estimator type
        if not self._estimator is None:
            subelement = ET.SubElement(element, "estimator")
            subelement.text = self._estimator

        # Optional Triggers
        for trigger in self._triggers:
            trigger.get_trigger_xml(element)

        return element


    def find_filter(self, filter_type, bins):

        filter = None

        for test_filter in self._filters:

            # Determine if the Filter has the same type as the one requested
            if test_filter._type != filter_type:
                continue

            # Determine if the Filter has the same bin edges as the one requested
            elif test_filter._bins != bins:
                continue

            else:
                filter = test_filter
                break

        # If we found the Filter, return it
        if not filter is None:
            return filter

        # Otherwise, throw an Exception
        else:
            msg = 'Unable to find filter type {0} with bin edges {1} in ' \
                  'Tally ID={2}'.format(filter_type, bins, self._id)
            raise ValueError(msg)


    def get_score_index(self, score):

        try:
            index = self._scores.index(score)

        except ValueError:
            msg = 'Unable to get the score index for Tally since {0} ' \
                  'is not one of the bins'.format(bin)
            raise ValueError(msg)

        return index


    def get_value(self, score, filters, filter_bins, nuclide=None, value='mean'):
        """Returns a tally score value given a list of filters to satisfy.

        Parameters
        ----------
        score : str
              The score string of interest

        filters : list
              A list of the filters of interest

        filter_bins : list
              A list of the filter bins of interest. These are integers for
              material, surface, cell, cellborn, distribcell, universe filters,
              and floats for energy or energyout filters. The bins are tuples
              of three integers (x,y,z) for mesh filters. The order of the bins
              in the list is assumed to correspond to the order of the filters.

        nuclide : Nuclide
              The Nuclide of interest

        value : str
              A string for the type of value to return ('mean' (default), 'std_dev',
              'sum', or 'sum_sq' are accepted)
        """

        # Determine the score index from the score string
        score_index = self._scores.index(score)

        # Determine the nuclide index from the nuclide string/object
        if not nuclide is None:
            nuclide_index = self._nuclides.index(nuclide)
        else:
            nuclide_index = 0

        # Initialize index for Filter in Tally.results[:,:,:]
        filter_index = 0

        # Iterate over specified Filters to compute filter index
        for i, filter in enumerate(filters):

            # Find the equivalent Filter in this Tally's list of Filters
            test_filter = self.find_filter(filter._type, filter._bins)

            # Filter bins for a mesh are an (x,y,z) tuple
            if filter._type == 'mesh':

                # Get the dimensions of the corresponding mesh
                nx, ny, nz = test_filter._mesh._dimension

                # Convert (x,y,z) to a single bin -- this is similar to
                # subroutine mesh_indices_to_bin in openmc/src/mesh.F90.
                val = ((filter_bins[i][0] - 1) * ny * nz +
                       (filter_bins[i][1] - 1) * nz +
                       (filter_bins[i][2] - 1))
                filter_index += val * test_filter._stride

            # Filter bins for distribcell are the "IDs" of each unique placement
            # of the Cell in the Geometry (integers starting at 0)
            elif filter._type == 'distribcell':
                bin = filter_bins[i]
                filter_index += bin * test_filter._stride

            else:
                bin = filter_bins[i]
                bin_index = test_filter.get_bin_index(bin)
                filter_index += bin_index * test_filter._stride

        # Return the desired result from Tally
        if value == 'mean':
            return self._mean[filter_index, nuclide_index, score_index]
        elif value == 'std_dev':
            return self._std_dev[filter_index, nuclide_index, score_index]
        elif value == 'sum':
            return self._sum[filter_index, nuclide_index, score_index]
        elif value == 'sum_sq':
            return self._sum_sq[filter_index, nuclide_index, score_index]
        else:
            msg = 'Unable to return results from Tally ID={0} for score {1} ' \
                  'since the value {2} is not \'mean\', \'std_dev\', ' \
                  '\'sum\', or \'sum_sq\''.format(self._id, score, value)
            raise LookupError(msg)


    def export_results(self, filename='tally-results', directory='.',
                      format='hdf5', append=True):
        """Returns a tally score value given a list of filters to satisfy.

        Parameters
        ----------
        filename : str
              The name of the file for the results (default is 'tally-results')

        directory : str
              The name of the directory for the results (default is '.')

        format : str
              The format for the exported file - HDF5 ('hdf5', default), Python
              pickle ('pkl'), comma-separated values ('csv') files are supported.

        append : bool
              Whether or not to append the results to the file (default is True)
        """

        if not is_string(filename):
            msg = 'Unable to export the results for Tally ID={0} to ' \
                  'filename={1} since it is not a ' \
                  'string'.format(self._id, filename)
            raise ValueError(msg)

        elif not is_string(directory):
            msg = 'Unable to export the results for Tally ID={0} to ' \
                  'directory={1} since it is not a ' \
                  'string'.format(self._id, directory)
            raise ValueError(msg)

        elif not format in ['hdf5', 'pkl', 'csv']:
            msg = 'Unable to export the results for Tally ID={0} to ' \
                  'format {1} since it is not supported'.format(self._id, format)
            raise ValueError(msg)

        elif not isinstance(append, (bool, np.bool)):
            msg = 'Unable to export the results for Tally ID={0} since the ' \
                  'append parameters is not True/False'.format(self._id, append)
            raise ValueError(msg)

        # Make directory if it does not exist
        if not os.path.exists(directory):
            os.makedirs(directory)


        # HDF5 binary file
        if format == 'hdf5':

            import h5py

            filename = directory + '/' + filename + '.h5'

            if append:
                tally_results = h5py.File(filename, 'a')
            else:
                tally_results = h5py.File(filename, 'w')

            # Create an HDF5 group within the file for this particular Tally
            tally_group = tally_results.create_group('Tally-{0}'.format(self._id))

            # Add basic Tally data to the HDF5 group
            tally_group.create_dataset('id', data=self._id)
            tally_group.create_dataset('name', data=self._name)
            tally_group.create_dataset('estimator', data=self._estimator)
            tally_group.create_dataset('scores', data=np.array(self._scores))

            # Add a string array of the nuclides to the HDF5 group
            nuclides = []

            for nuclide in self._nuclides:
                nuclides.append(nuclide._name)


            tally_group.create_dataset('nuclides', data=np.array(nuclides))

            # Create an HDF5 sub-group for the Filters
            filter_group = tally_group.create_group('filters')

            for filter in self._filters:
                filter_group.create_dataset(filter._type, data=filter._bins)

            # Add all results to the main HDF5 group for the Tally
            tally_group.create_dataset('sum', data=self._sum)
            tally_group.create_dataset('sum_sq', data=self._sum_sq)
            tally_group.create_dataset('mean', data=self._mean)
            tally_group.create_dataset('std_dev', data=self._std_dev)

            # Close the Tally results HDF5 file
            tally_results.close()


        # Python pickle binary file
        elif format == 'pkl':

            import pickle

            # Load the dictionary from the Pickle file
            filename = directory + '/' + filename + '.pkl'

            if os.path.exists(filename) and append:
                tally_results = pickle.load(file(filename, 'rb'))
            else:
                tally_results = {}

            # Create a nested dictionary within the file for this particular Tally
            tally_results['Tally-{0}'.format(self._id)] = {}
            tally_group = tally_results['Tally-{0}'.format(self._id)]

            # Add basic Tally data to the nested dictionary
            tally_group['id'] = self._id
            tally_group['name'] = self._name
            tally_group['estimator'] = self._estimator
            tally_group['scores'] = np.array(self._scores)

            # Add a string array of the nuclides to the HDF5 group
            nuclides = []

            for nuclide in self._nuclides:
                nuclides.append(nuclide._name)

            tally_group['nuclides']= np.array(nuclides)

            # Create a nested dictionary for the Filters
            tally_group['filters'] = {}
            filter_group = tally_group['filters']

            for filter in self._filters:
                filter_group[filter._type] = filter._bins

            # Add all results to the main sub-dictionary for the Tally
            tally_group['sum'] = self._sum
            tally_group['sum_sq'] = self._sum_sq
            tally_group['mean'] = self._mean
            tally_group['std_dev'] = self._std_dev

            # Pickle the Tally results to a file
            pickle.dump(tally_results, open(filename, 'wb'))


class TalliesFile(object):

    def __init__(self):

        # Initialize TalliesFile class attributes
        self._tallies = []
        self._meshes = []
        self._tallies_file = ET.Element("tallies")


    def add_tally(self, tally, merge=False):

        if not isinstance(tally, Tally):
            msg = 'Unable to add a non-Tally {0} to the TalliesFile'.format(tally)
            raise ValueError(msg)

        if merge:
            merged = False

            # Look for a tally to merge with this one
            for i, tally2 in enumerate(self._tallies):

                # If a mergeable tally is found
                if tally2.can_merge(tally):

                    # Replace tally 2 with the merged tally
                    merged_tally = tally2.merge(tally)
                    self._tallies[i] = merged_tally
                    merged = True

            # If not mergeable tally was found, simply add this tally
            if not merged:
                self._tallies.append(tally)

        else:
            self._tallies.append(tally)


    def remove_tally(self, tally):
        self._tallies.remove(tally)


    def merge_tallies(self):

        for i, tally1 in enumerate(self._tallies):
            for j, tally2 in enumerate(self._tallies):

                # Do not merge the same tally with itself
                if i == j:
                    continue

                # If the two tallies are mergeable
                if tally1.can_merge(tally2):

                    # Replace tally 1 with the merged tally
                    merged_tally = tally1.merge(tally2)
                    self._tallies[i] = merged_tally

                    # Remove tally 2 since it is no longer neede
                    self._tallies.pop(j)

                    # Continue iterating from the first loop
                    break


    def add_mesh(self, mesh):

        if not isinstance(mesh, Mesh):
            msg = 'Unable to add a non-Mesh {0} to the TalliesFile'.format(mesh)
            raise ValueError(msg)

        self._meshes.append(mesh)


    def remove_mesh(self, mesh):
        self._meshes.remove(mesh)


    def create_tally_subelements(self):

        for tally in self._tallies:
            xml_element = tally.get_tally_xml()
            self._tallies_file.append(xml_element)


    def create_mesh_subelements(self):

        for mesh in self._meshes:

            if len(mesh._name) > 0:
                self._tallies_file.append(ET.Comment(mesh._name))

            xml_element = mesh.get_mesh_xml()
            self._tallies_file.append(xml_element)


    def export_to_xml(self):

        self.create_mesh_subelements()
        self.create_tally_subelements()

        # Clean the indentation in the file to be user-readable
        clean_xml_indentation(self._tallies_file)

        # Write the XML Tree to the tallies.xml file
        tree = ET.ElementTree(self._tallies_file)
        tree.write("tallies.xml", xml_declaration=True,
                             encoding='utf-8', method="xml")
