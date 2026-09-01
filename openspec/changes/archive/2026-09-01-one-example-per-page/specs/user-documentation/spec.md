## MODIFIED Requirements

### Requirement: Worked examples demonstrate the released capabilities

The documentation SHALL present worked example projects whose pinned sources
actually contain what the documentation claims of them, and at least one
example SHALL demonstrate the released machine surface: declared drivers,
machine-level instructions, and flexible parts.

Each worked example SHALL live on its own page, reached from an examples
index page that embeds no model of its own, so that opening one example
loads one live model rather than every example at once.

#### Scenario: An example's description matches its pinned source

- **WHEN** a reader follows an example's source link at the documented
  pinned revision
- **THEN** every capability the example's page attributes to it is present
  in that revision's source

#### Scenario: A machine example exists

- **WHEN** a reader looks for a full-machine example
- **THEN** the documentation offers one whose root assembly declares drivers
  and instructions and whose parts include flexible leaves

#### Scenario: Opening one example loads one model

- **WHEN** a reader opens the page of a worked example
- **THEN** that page embeds exactly one live model, and no other worked
  example's model is loaded by it

#### Scenario: Reaching the examples

- **WHEN** a reader opens the examples index
- **THEN** it links to every worked example's page and embeds no live model
  itself
