package pyextensions

import newrelic.jenkins.extensions
import javaposse.jobdsl.dsl.Job


public class pyextensions extends extensions {
    static void labelParam(Job job, String labelName, String labelDefaultValue,
            String descriptionValue) {
        job.configure {
            it / 'properties' /
                    'hudson.model.ParametersDefinitionProperty' /
                    'parameterDefinitions' <<
                    'org.jvnet.jenkins.plugins.nodelabelparameter.LabelParameterDefinition' {
                name labelName
                description descriptionValue
                defaultValue labelDefaultValue
                allNodesMatchingLabel(true)
                triggerIfResult('allCases')
                nodeEligibility(class: 'org.jvnet.jenkins.plugins.nodelabelparameter.node.AllNodeEligibility')
            }
        }
    }

    static void blockOn(Job job, String blockers) {
        job.configure {
            it / 'properties' /
                    'hudson.plugins.buildblocker.BuildBlockerProperty' {
                blockingJobs blockers
                useBuildBlocker true
                blockLevel 'GLOBAL'
                scanQueueFor 'DISABLED'
            }
        }
    }
}
