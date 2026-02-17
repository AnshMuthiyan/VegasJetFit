from VegasAfterglow import VegasAfterglowC as vac

def rho(r, theta, phi):
    return 1.0

print("Positional:")
try:
    m1 = vac.Medium(rho)
    print("  OK")
except Exception as e:
    print("  FAIL:", e)

print("Keyword:")
try:
    m2 = vac.Medium(rho=rho)
    print("  OK")
except Exception as e:
    print("  FAIL:", e)

