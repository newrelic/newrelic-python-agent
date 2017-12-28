import hudson.model.*
import jenkins.model.*

def mmfBranch = build.getEnvironment()["GIT_REPOSITORY_BRANCH"]

def eVarMmfBranch = new StringParameterValue("GIT_REPOSITORY_BRANCH", mmfBranch)
def paramsAction = new ParametersAction(eVarMmfBranch)
build.replaceAction(paramsAction)

build.setDescription("MMF branch: ${mmfBranch}")
