# Purpose: Reproduce the duplicate-coordinate abort in the old user hook and verify conservative handling plus conflicting-volume rejection in the corrected hook.
from pathlib import Path
import json
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EVIDENCE = HERE / "geometry_alias_regression"
build = json.loads((HERE / "user_module_only_build/build.json").read_text())
work = Path(tempfile.mkdtemp(prefix="geometry-alias-check-"))
source_tree = Path(build["temporary_build"]) / "source"
(work / "amrvac.h").write_bytes((ROOT / "amrvac.h").read_bytes())
old_source = work / "before_mod_usr.t"
old_source.write_bytes((EVIDENCE / "before_mod_usr.t").read_bytes())
old_generated = subprocess.run(
    ["perl", str(source_tree / "src/vacpp.pl"), "-d=1", "-v=1", str(old_source)],
    cwd=work, text=True, capture_output=True, check=True,
).stdout
new_generated = (Path(build["temporary_build"]) / "problem/mod_usr.f").read_text()

# Minimal state storage; the procedure under test is copied verbatim from
# AMRVAC-preprocessed user code, not reimplemented in this harness.
stub = """! Purpose: Isolate the actual user refinement procedure with controlled coordinate/volume aliases.
module mod_global_parameters
  implicit none
  integer, parameter :: ndim=1,nw=3,rho_=1,e_=3,mom(1)=[2]
  integer :: it=123,mype=0
  double precision, parameter :: one=1.d0,zero=0.d0,half=0.5d0
  double precision :: small_pressure=1.d-14,small_density=1.d-14,hd_gamma=5.d0/3.d0
  type state
    double precision, allocatable :: w(:,:)
    double precision, pointer :: x(:,:)=>null(),dvolume(:)=>null()
  end type state
  type(state), allocatable :: ps(:)
contains
  subroutine mpistop(message)
    character(len=*), intent(in) :: message
    print *, trim(message)
    stop 128
  end subroutine mpistop
end module mod_global_parameters
module user_hook_under_test
  implicit none
  double precision :: amr_pair_events=0.d0,amr_pair_worst=0.d0
  logical :: amr_geometry_alias_reported=.false.
contains
"""
driver = """
end module user_hook_under_test
program test_refinement_geometry
  use mod_global_parameters
  use user_hook_under_test
  use, intrinsic :: ieee_arithmetic, only: ieee_value,ieee_quiet_nan
  implicit none
  character(len=32) :: mode
  double precision :: w(4,3),x(4,1),before(3),after(3)
  integer :: j
  call get_command_argument(1,mode)
  allocate(ps(2))
  x(:,1)=[0.2d0,0.3d0,0.4d0,0.5d0]
  do j=1,2
    allocate(ps(j)%w(4,3),ps(j)%x(4,1),ps(j)%dvolume(4))
    ps(j)%x=x
    ps(j)%dvolume=[1.d0,3.d0,2.d0,4.d0]
  enddo
  if(mode=='unique') ps(2)%x=x+1.d0
  if(mode=='conflict') ps(2)%dvolume(1)=2.d0
  if(mode=='roundoff') ps(2)%dvolume(1)=1.d0+8.d0*epsilon(1.d0)
  if(mode=='nan_volume') ps(2)%dvolume(1)=ieee_value(1.d0,ieee_quiet_nan)
  if(mode=='negative_volume') ps(2)%dvolume(1)=-1.d0
  w(:,1)=1.d0
  w(:,2)=[4.d0,0.d0,0.d0,0.d0]
  w(:,3)=[1.d0,10.d0,2.d0,2.d0]
  before=ps(1)%dvolume(1)*w(1,:)+ps(1)%dvolume(2)*w(2,:)
  call conservative_refinement(1,4,1,4,w,x)
  after=ps(1)%dvolume(1)*w(1,:)+ps(1)%dvolume(2)*w(2,:)
  if(any(abs(after-before)>32.d0*epsilon(1.d0)*max(abs(before),tiny(1.d0)))) stop 2
  if(any(w(1,:)/=w(2,:))) stop 3
  if(any(w(1,:)/=[1.d0,1.d0,7.75d0])) stop 4
  if(any(w(3,:)/=[1.d0,0.d0,2.d0]).or.any(w(4,:)/=[1.d0,0.d0,2.d0])) stop 5
  if(amr_pair_events/=1.d0.or.amr_pair_worst>1.d-12) stop 6
  print *, 'CONSERVATIVE ALIAS CHECK PASSED: ',trim(mode)
end program test_refinement_geometry
"""
results = []
for version, generated in (("before", old_generated), ("after", new_generated)):
    procedure = generated.split("  subroutine conservative_refinement(", 1)[1]
    procedure = "  subroutine conservative_refinement(" + procedure.split(
        "  end subroutine conservative_refinement", 1
    )[0] + "  end subroutine conservative_refinement\n"
    code = work / f"{version}.f90"
    code.write_text(stub + procedure + driver)
    subprocess.run(["gfortran", "-ffree-line-length-none", "-fcheck=all", "-O2",
                    str(code), "-o", str(work / version)], cwd=work, check=True)
    modes = ("unique", "equivalent") if version == "before" else (
        "unique", "equivalent", "roundoff", "conflict", "nan_volume", "negative_volume"
    )
    for mode in modes:
        completed = subprocess.run([str(work / version), mode], text=True, capture_output=True)
        output = completed.stdout + completed.stderr
        expected = {"conflict": "Coordinate-matched refinement volumes disagree",
                    "nan_volume": "Nonfinite coordinate-matched refinement volumes",
                    "negative_volume": "Nonpositive coordinate-matched refinement volumes"}.get(mode)
        if version == "before" and mode == "equivalent":
            expected = "Ambiguous fine-block geometry in user refinement"
        if expected:
            assert completed.returncode != 0 and expected in output, output
        else:
            assert completed.returncode == 0 and "CONSERVATIVE ALIAS CHECK PASSED" in output, output
        results.append({"version": version, "case": mode, "returncode": completed.returncode,
                        "expected_rejection": expected, "passed": True, "output": output})
        print(version, mode, "PASSED", flush=True)
report = {"purpose": "Prove the old duplicate-coordinate failure and verify the corrected conservative geometry selection and fail-fast controls.",
          "scope": "Actual preprocessed user procedure with controlled state storage; VM checkpoint test0050.dat was not available locally.",
          "core_source_modified": False, "cases": results}
(EVIDENCE / "results.json").write_text(json.dumps(report, indent=2) + "\n")
print("ALL GEOMETRY ALIAS CHECKS PASSED", flush=True)
