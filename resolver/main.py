from pip._internal.resolution.resolvelib.resolver import Resolver
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.cli.req_command import RequirementCommand
from pip._internal.commands.install import InstallCommand
from pip._internal.network.session import PipSession
from pip._internal.req import req_tracker, constructors
from pip._internal.req.constructors import install_req_from_req_string
from pip._internal.cli.cmdoptions import make_target_python
from pip._internal.utils import temp_dir

requirement_string = "boto3"

requirement = install_req_from_req_string(
    req_string=requirement_string,
    user_supplied=True,
)

py_version_info = None

install_command = InstallCommand(name="install", summary="Installs, but not really.", isolated=True)
options, _ = install_command.parse_args([])
pip_session = PipSession()

target_python = make_target_python(options)
finder = install_command._build_package_finder(
    options=options,
    session=pip_session,
    target_python=target_python,
    ignore_requires_python=options.ignore_requires_python,
)

with req_tracker.get_requirement_tracker() as req_tracker_:
    with temp_dir.global_tempdir_manager():
        temp_build_dir = temp_dir.TempDirectory("build", delete=True, globally_managed=True)
        temp_download_dir = temp_dir.TempDirectory("download", delete=True, globally_managed=True).path

        preparer: RequirementPreparer = InstallCommand.make_requirement_preparer(
            temp_build_dir=temp_build_dir,
            options=options,
            req_tracker=req_tracker_,
            session=pip_session,
            finder=finder,
            use_user_site=False,
            download_dir=temp_download_dir,
        )

        resolver: Resolver = InstallCommand.make_resolver(
            preparer=preparer,
            finder=finder,
            options=options,
            wheel_cache=None,
            use_user_site=False,
            ignore_installed=True,
            ignore_requires_python=True,
            py_version_info=py_version_info,
        )

        test = resolver.resolve(
            root_reqs=[
                requirement,
            ],
            check_supported_wheels=None
        )

        print(repr(test))
        print("Done.")

# TODO: This pulls in all dependencies recursively. We just want the top-level dependencies.
