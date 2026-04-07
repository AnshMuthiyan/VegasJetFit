Apply this patch on top of the `VegasAfterglow` `v2.0.1` source tree to get the Dylan smoothing / GS02 medium updates used by the current JetFit branch.

Recommended workflow:

```bash
git clone https://github.com/YihanWangAstro/VegasAfterglow.git
cd VegasAfterglow
git checkout v2.0.1
git am /path/to/VegasJetFit/patches/vegasafterglow/0001-Publish-Dylan-smoothing-engine-updates.patch
```

If the checkout is not a git clone, use `git apply` instead of `git am`.
