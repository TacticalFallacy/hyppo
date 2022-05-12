import numpy as np
from numba import jit
from hyppo.ksample.base import KSampleTest
from hyppo.ksample._utils import _CheckInputs
from sklearn.metrics import pairwise_distances
from scipy.stats import ks_2samp


class HHG(KSampleTest):
    r"""
    HHG 2-Sample test statistic.
    
    This is a 2-sample multivariate test based on univariate test statistics.
    It inherits the computational complexity from the unvariate tests to achieve
    faster speeds than classic multivariate tests.
    The univariate test used is the Kolmogorov-Smirnov 2-sample test.
    :footcite:p:`hellerMultivariateTestsOfAssociation2016`.
    
    Notes
    -----
    The statistic can be derived as follows:
    :footcite:p:`hellerMultivariateTestsOfAssociation2016`.
    
    Let :math:`x`, :math:`y` be :math:`(n, p)`, :math:`(m, p)` samples of random variables
    :math:`X` and :math:`Y \in \R^p` . Let there be a center point
    :math:`\in \R^p`. 
    For every sample :math:`i`, calculate the distances from the center point
    in :math:`x` and :math:`y` and denote this as :math:`d_x(x_i)`
    and :math:`d_y(y_i)`. This will create a 1D collection of distances for each
    sample group.
    
    Then apply the KS 2-sample test on these center-point distances. This classic test
    compares the empirical distribution function of the two samples and takes
    the supremum of the difference between them. See Notes under scipy.stats.ks_2samp
    for more details.
    
    To achieve better power, the above process is repeated with each sample point 
    :math:`x_i` and :math:`y_i` as center points. The resultant :math:`n+m` p-values
    are then pooled for use in the Bonferroni test of the global null hypothesis.
    The HHG statistic is the KS stat associated with the smallest p-value from the pool,
    while the HHG p-value is the smallest p-value multipled by the number of sample points.
    
    References
    ----------
    .. footbibliography::
    """

    def __init__(self, compute_distance="euclidean", **kwargs):
        self.compute_distance = compute_distance
        KSampleTest.__init__(self, compute_distance=compute_distance, **kwargs)

    def statistic(self, x, y):
        """
        x,y : ndarray of float
            Input data matrices. ``x`` and ``y`` must have the same number of
            dimensions. That is, the shapes must be ``(n, p)`` and ``(m, p)`` where
            `n` and  are the number of samples and `p` is the number of
            dimensions.
            
        Returns
        -------
        stat : float
            The computed KS test statistic associated with the lowest p-value.
        """
        xy = np.concatenate((x, y), axis=0)
        distxy = _centerpoint_dist(xy, self.compute_distance, 1)
        distx = distxy[:, 0 : len(x)]
        disty = distxy[:, len(x) : len(x) + len(y)]
        stats, pvalues = _distance_score(distx, disty)
        minP = min(pvalues)
        minstat = stats[pvalues.index(minP)]
        self.stat = minstat
        return self.stat

    def test(self, x, y):
        """
        x,y : ndarray of float
            Input data matrices. ``y1`` and ``y2`` must have the same number of
            dimensions. That is, the shapes must be ``(n, p)`` and ``(m, p)`` where
            `n` and `m` are the number of samples and `p` is the number of
            dimensions.
            
        Returns
        -------
        stat : float
            The computed KS test statistic associated with the lowest p-value.
        pvalue : float
            The computed HHG pvalue. Equivalent to the lowest p-value multiplied by the total number
            of samples.
        """
        check_input = _CheckInputs(inputs=[x, y],)
        x, y = check_input()

        xy = np.concatenate((x, y), axis=0)
        distxy = _centerpoint_dist(xy, self.compute_distance, 1)
        distx = distxy[:, 0 : len(x)]
        disty = distxy[:, len(x) : len(x) + len(x)]
        stats, pvalues = _distance_score(distx, disty)
        minP = min(pvalues)
        minstat = stats[pvalues.index(minP)]
        pvalue = minP * len(pvalues)
        return minstat, pvalue


def _centerpoint_dist(xy, metric, workers=1, **kwargs):
    """Gives pairwise distances - each row corresponds to center-point distances
    where one sample point is the center point"""
    distxy = pairwise_distances(xy, metric=metric, n_jobs=workers, **kwargs)
    return distxy


def _distance_score(distx, disty):
    dist1, dist2 = _extract_distance(distx, disty)
    stats = []
    pvalues = []
    for i in range(len(distx)):
        stat, pvalue = ks_2samp(dist1[i], dist2[i])
        stats.append(stat)
        pvalues.append(pvalue)
    return stats, pvalues


@jit(nopython=True)
def _extract_distance(distx, disty):
    """Process distance arrays into list of distances"""
    dist1 = []
    dist2 = []
    for i in range(len(distx)):
        distancex = np.delete(distx[i], 0)
        distancey = np.delete(disty[i], 0)
        distancex = distancex.reshape(-1)
        distancey = distancey.reshape(-1)
        dist1.append(distancex)
        dist2.append(distancey)
    return dist1, dist2
