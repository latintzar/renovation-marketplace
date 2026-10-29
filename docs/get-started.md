# First result

Run the original app with its real backend and private local records:

```sh
make install
make doctor
make build
make dev
```

Open **http://127.0.0.1:18260/app/**. Choose the saved quote, edit it, save it and reload. Project messages and submitted phase proof persist through the same backend. Each visitor has a separate workspace.

[Native workspace](native-workspace.md) covers entry points, module flow, stored records, limits, credentials and deployment. [Setup](setup.md) covers recipient-owned Supabase, Hermes, Stripe and delivery services. The original [scripted walkthroughs](historical-walkthroughs.md) remain a separately selected historical presentation.

[made by atelier neyra](https://atelierneyra.com)
