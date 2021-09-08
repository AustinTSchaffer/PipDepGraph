from pip._internal.resolution.resolvelib.resolver import Resolver
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.cli.req_command import RequirementCommand
from pip._internal.commands.install import InstallCommand
from pip._internal.network.session import PipSession
from pip._internal.req import req_tracker, constructors
from pip._internal.req.constructors import install_req_from_req_string
from pip._internal.cli.cmdoptions import make_target_python
from pip._internal.utils import temp_dir
from pip._internal.resolution.resolvelib.provider import PipProvider
from pip._vendor.resolvelib import Resolver as RLResolver
from pip._vendor.resolvelib import resolvers as rl_resolvers
from pip._internal.resolution.resolvelib.reporter import (
    PipDebuggingReporter,
    PipReporter,
)

# TODO: These will come into play at some point. Will need to iterate
# over combinations of these. These are effectively the inputs.
package_name = "boto3"
requirement_string = "boto3==1.18.12"
platforms = []
py_versions = []
py_version_info = None

#
# Boilerplate Bonanza Below
#
requirement = install_req_from_req_string(
    req_string=requirement_string,
    user_supplied=True,
)

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
    # TODO: Fix tempdir stuff
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

        collected = resolver.factory.collect_root_requirements([requirement])
        provider = PipProvider(
            factory=resolver.factory,
            constraints=collected.constraints,
            ignore_dependencies=resolver.ignore_dependencies,
            upgrade_strategy=resolver.upgrade_strategy,
            user_requested=collected.user_requested,
        )

        class TopLevelRequirementResolution(rl_resolvers.Resolution):
            def __init__(self, package_name, provider, reporter):
                super().__init__(provider=provider, reporter=reporter)
                self.package_name = package_name

            def _is_current_pin_satisfying(self, name, criterion):
                """
                Overrides rl_resolvers.Resolution._is_current_pin_satisfying to force satisfaction
                for packages that aren't the package we care about. This should reduce the total
                amount of packages that the resolver needs to download.
                """
                return (
                    True if name != self.package_name else
                    super()._is_current_pin_satisfying(name, criterion)
                )

        resolution = TopLevelRequirementResolution(package_name=package_name, provider=provider, reporter=PipReporter())
        state = resolution.resolve(collected.requirements, max_rounds=2)
        result = rl_resolvers._build_result(state)

        # Scrubs the results for the requirement info that's relevant to "package_name"
        direct_dependency_requirement_info = []
        for direct_dependency in result.graph.iter_children(package_name):
            criterion = result.criteria[direct_dependency]
            for req_info in criterion.information:
                if req_info.parent.name == package_name:
                    direct_dependency_requirement_info.append(req_info.requirement)

        from pprint import pprint
        pprint(direct_dependency_requirement_info)

        print("Done.")