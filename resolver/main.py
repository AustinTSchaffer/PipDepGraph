import contextlib
import logging
import sys

from pip._internal.commands.install import InstallCommand
from pip._internal.models.link import Link
from pip._internal.models.wheel import Wheel
from pip._internal.network.session import PipSession
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.req import req_tracker
from pip._internal.index.package_finder import _extract_version_from_fragment
from pip._internal.req.constructors import install_req_from_req_string
from pip._internal.resolution.resolvelib.candidates import LinkCandidate
from pip._internal.resolution.resolvelib.factory import Factory
from pip._internal.resolution.resolvelib.provider import PipProvider
from pip._internal.resolution.resolvelib.reporter import (PipDebuggingReporter,
                                                          PipReporter)
from pip._internal.utils import temp_dir, filetypes
from pip._vendor.packaging.version import Version
from pip._vendor.packaging.utils import canonicalize_name
from pip._internal.utils.unpacking import SUPPORTED_EXTENSIONS


logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

package_name = "pandas"
package_canonical_name = canonicalize_name(package_name)

# TODO: Need a link collector

package_url = "https://files.pythonhosted.org/packages/8f/d3/d994f9347b42407adc04e58fdeb5e52013df14bcc4a678c5211ffd526ebd/pandas-1.2.5-cp39-cp39-manylinux_2_5_x86_64.manylinux1_x86_64.whl#sha256=4bfbf62b00460f78a8bc4407112965c5ab44324f34551e8e1f4cac271a07706c"
package_link = Link(package_url)

egg_info, ext = package_link.splitext()
package_version = _extract_version_from_fragment(
    egg_info, package_canonical_name,
)

if ext == filetypes.WHEEL_EXTENSION:
    # If the package is a wheel, the filename contains additional
    # useful metadata about the package and its reportedly supported
    # plat/arch/OS/pyversion
    wheel = Wheel(package_link.filename)

if ext not in SUPPORTED_EXTENSIONS:
    raise ValueError(f"Can't do {ext}, but should record it somewhere.")

#
# Process Package Link
#

install_command = InstallCommand(
    name="install", summary="Installs, but not really.", isolated=True
)

options, _ = install_command.parse_args([])

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
            session=PipSession(),
            finder=None,
            use_user_site=False,
            download_dir=temp_download_dir,
        )

        factory = Factory(
            finder=None,
            preparer=preparer,
            make_install_req=None,
            wheel_cache=None,
            use_user_site=False,
            ignore_installed=True,
            force_reinstall=False,
            ignore_requires_python=True,
            py_version_info=None,
        )

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
