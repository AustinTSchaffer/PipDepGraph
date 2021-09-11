import contextlib
import logging
import sys

from pip._internal.cli.cmdoptions import make_target_python
from pip._internal.commands.install import InstallCommand
from pip._internal.index.package_finder import _extract_version_from_fragment
from pip._internal.models.link import Link
from pip._internal.models.wheel import Wheel
from pip._internal.network.session import PipSession
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.req import req_tracker
from pip._internal.req.constructors import install_req_from_req_string
from pip._internal.resolution.resolvelib.candidates import LinkCandidate
from pip._internal.resolution.resolvelib.factory import Factory
from pip._internal.resolution.resolvelib.provider import PipProvider
from pip._internal.resolution.resolvelib.reporter import (PipDebuggingReporter,
                                                          PipReporter)
from pip._internal.utils import filetypes, temp_dir
from pip._internal.utils.unpacking import SUPPORTED_EXTENSIONS
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.packaging.version import Version

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


# TODO: Need a link collector in order to iterate over all package links for a package.

# Probably shouldn't yank the hash off the end of the wheel.
package_name = "pandas"
package_url = "https://files.pythonhosted.org/packages/8f/d3/d994f9347b42407adc04e58fdeb5e52013df14bcc4a678c5211ffd526ebd/pandas-1.2.5-cp39-cp39-manylinux_2_5_x86_64.manylinux1_x86_64.whl"

# Windows test... Seems to work.
# TODO: Is this script necessary, or would the other one that more natively uses "pip install" work better?
#       Should I combine the pros and cons of each?
# package_name = "numpy"
# package_url = "https://files.pythonhosted.org/packages/26/2e/498c68b44f83d834fe3730b8a08d887ea23fdab51783a6ffa0c57d7dead8/numpy-1.21.0rc1-cp39-cp39-win32.whl#sha256=dcc194082d94c45fe8a005861cdce6ec33b51c1dccf2a7e6044b33038b82f579"

# This process doesn't seem to work perfectly for platform-independent "sdist" (tarball/zip) packages when debugging. Do we care?
# package_name = "pandas"
# package_url = "https://files.pythonhosted.org/packages/ab/5c/b38226740306fd73d0fea979d10ef0eda2c7956f4b59ada8675ec62edba7/pandas-1.2.5.tar.gz#sha256=14abb8ea73fce8aebbb1fb44bec809163f1c55241bcc1db91c2c780e97265033"

package_canonical_name = canonicalize_name(package_name)
package_link = Link(package_url)

egg_info, ext = package_link.splitext()
package_version = _extract_version_from_fragment(
    egg_info, package_canonical_name,
)

if ext not in SUPPORTED_EXTENSIONS:
    raise ValueError(f"Can't do {ext}, but should record it somewhere.")

if ext == filetypes.WHEEL_EXTENSION:
    # If the package is a wheel, the filename contains additional
    # useful metadata about the package and its reportedly supported
    # plat/arch/OS/pyversion
    wheel = Wheel(package_link.filename)
    package_version = wheel.version

#
# Process Package Link. A lot of the code between here and the next major
# comment is boilerplate dependency injection. We need a preparer and a factory
# to property download the package blob, extract it, and run setup.py and/or
# parse the metadata.
#

install_command = InstallCommand(
    name="install", summary="Installs, but not really.", isolated=True
)

options, _ = install_command.parse_args([])

pip_session = PipSession()

# finder is required when the package is not a wheel. Not sure why.
finder = install_command._build_package_finder(
    options=options,
    session=pip_session,
    target_python=make_target_python(options),
    ignore_requires_python=options.ignore_requires_python,
)

with req_tracker.get_requirement_tracker() as req_tracker_:
    # TODO: Fix tempdir stuff
    with temp_dir.global_tempdir_manager():
        temp_build_dir = temp_dir.TempDirectory(
            "build", delete=True, globally_managed=True
        )

        temp_download_dir = temp_dir.TempDirectory(
            "download", delete=True, globally_managed=True
        ).path

        preparer: RequirementPreparer = InstallCommand.make_requirement_preparer(
            temp_build_dir=temp_build_dir,
            options=options,
            req_tracker=req_tracker_,
            session=pip_session,
            finder=finder,
            use_user_site=False,
            download_dir=temp_download_dir,
        )

        factory = Factory(
            finder=finder,
            preparer=preparer,
            make_install_req=None,
            wheel_cache=None,
            use_user_site=False,
            ignore_installed=True,
            force_reinstall=False,
            ignore_requires_python=True,
            py_version_info=None,
        )

        #
        # Initializing this class downloads the file and parses the package's requirements
        #

        candidate = LinkCandidate(
            link=package_link,
            factory=factory,
            template=install_req_from_req_string(package_name),
            name=package_name,
            version=Version(package_version),
        )

        #
        # :tada:
        #

        dist = candidate.dist
        requirements = candidate.dist.requires()

        import pprint
        pprint.pprint(candidate)
