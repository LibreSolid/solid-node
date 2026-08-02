## ADDED Requirements

### Requirement: Distributions carry a built viewer bundle

Source distributions and wheels of the framework SHALL contain the built viewer
bundle alongside the built development app. Creating a source distribution SHALL
build the viewer bundle; creating a wheel SHALL build it when the checkout does
not already contain one, and SHALL keep an existing one. An installed framework
therefore SHALL provide the bundle without any npm step by its user.

#### Scenario: A source distribution is created

- **WHEN** a source distribution is built from a checkout with no built viewer
- **THEN** the viewer bundle is built during packaging and is present in the
  distribution

#### Scenario: A wheel is created from a checkout that already built the viewer

- **WHEN** a wheel is built from a checkout containing a built viewer bundle
- **THEN** packaging does not rebuild it and the wheel contains that bundle

#### Scenario: A wheel is created from a checkout with no built viewer

- **WHEN** a wheel is built from a checkout with no built viewer bundle
- **THEN** packaging builds it and the wheel contains it

### Requirement: An installed framework reports its viewer

The framework SHALL report, to a program that does not import it, the filesystem
path of its built viewer bundle and the integer API version the viewer declares,
as one machine-readable result on standard output. The reported path SHALL be
absolute and SHALL exist. When the installation carries no built bundle, the
framework SHALL instead report a failure that names the remedy and SHALL exit
non-zero, so that a consumer distinguishes an absent viewer from an unreadable
result without interpreting prose.

#### Scenario: A host asks an installed framework for the viewer

- **WHEN** a program runs the framework's viewer report against an installation
  containing a built bundle
- **THEN** it receives, on standard output, the absolute path of an existing
  bundle file and the declared viewer API version, and the process exits zero

#### Scenario: A host asks an installation that has no bundle

- **WHEN** a program runs the viewer report against an installation with no
  built bundle
- **THEN** the process exits non-zero, standard output carries no result, and
  the message names how to obtain a bundle

#### Scenario: The reported version is the viewer's declared version

- **WHEN** a host compares the reported API version with the version the mounted
  viewer reports
- **THEN** they are the same integer

### Requirement: One answer about the bundle across framework channels

Every framework channel that needs the viewer bundle — the viewer report, static
export, and documentation embedding — SHALL resolve it from the same declared
location and SHALL name the same remedy when it is absent. Documentation
embedding SHALL continue to resolve the bundle without loading the CAD runtime.

#### Scenario: Export and documentation embedding disagree about nothing

- **WHEN** the bundle is absent and an export and a documentation build each
  report it
- **THEN** both name the same location and the same remedy

#### Scenario: A documentation build stays free of the CAD runtime

- **WHEN** a documentation build completes an export that was made without
  viewer files
- **THEN** it copies the bundle from the installed framework without importing
  the framework's CAD runtime
