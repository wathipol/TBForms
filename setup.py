import setuptools
with open("README.md", "r") as fh:
	long_description = fh.read()

requirements = [
    "pyTelegramBotAPI",
    "dill"

]

setuptools.setup(
	name="TBForms",
	version="0.9.4",
	author="watdev",
	author_email="v.liubachevskyi@gmail.com",
	description="Small extension for pyTelegramBotAPI library for building interactive forms in Telegram bots.",
	long_description=long_description,
	long_description_content_type="text/markdown",
	url="https://github.com/wathipol/TBForms",
	packages=setuptools.find_packages(),
	install_requires=requirements,
	classifiers=[
		"Programming Language :: Python :: 3.8",
		"License :: OSI Approved :: MIT License",
		"Operating System :: OS Independent",
	],
	python_requires='>=3.6',
)
