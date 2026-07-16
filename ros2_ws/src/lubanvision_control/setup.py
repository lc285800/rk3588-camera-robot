from setuptools import find_packages, setup


package_name = "lubanvision_control"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="lc285800",
    maintainer_email="lc285800@users.noreply.github.com",
    description="ROS-independent control primitives for LubanVision.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "simulation_probe = "
            "lubanvision_control.simulation_probe:main",
        ],
    },
)
