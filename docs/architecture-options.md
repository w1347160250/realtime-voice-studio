# Architecture Options

## Option A: Web first

Best when:

- you want fast iteration
- users can open a browser
- the first goal is validating conversation quality and latency

Pros:

- fastest to prototype
- easiest to demo and distribute
- can later become a desktop app with a wrapper

Risks:

- browser permission handling can be annoying
- some system-level integrations are harder than native apps

## Option B: Desktop first

Best when:

- you need deep OS integration
- you want a dedicated always-on tool
- your users are mostly internal staff on managed devices

Pros:

- better control over audio devices and local integrations
- more product-like than a browser tab

Risks:

- higher development and packaging cost
- slower iteration early on

## Option C: Mobile first

Best when:

- the usage moment is on the go
- headset, phone, and mobility matter more than desktop workflow

Pros:

- best fit for mobile scenarios

Risks:

- most expensive route for an uncertain product
- harder debugging during early discovery

## Recommendation for now

Start with `Web first` unless one of these is true:

- you need system audio capture
- you need tray app behavior
- you need deep integration with local desktop software

If the product proves useful, we can package the same interaction model into a desktop shell later.