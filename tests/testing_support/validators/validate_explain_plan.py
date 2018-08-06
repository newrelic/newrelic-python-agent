from newrelic.common.object_wrapper import transient_function_wrapper


def validate_stats_engine_explain_plan_output_is_not_none():
    """This fixture isn't useful by itself, because you need to generate
    explain plans, which doesn't normally occur during record_transaction().

    Use the `validate_transaction_slow_sql_count` fixture to force the
    generation of slow sql data after record_transaction(), which will run
    newrelic.core.stats_engine.explain_plan.

    """
    @transient_function_wrapper('newrelic.core.stats_engine',
            'explain_plan')
    def _validate_explain_plan_output_is_not_none(wrapped, instance, args,
            kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            assert result is not None

        return result

    return _validate_explain_plan_output_is_not_none
