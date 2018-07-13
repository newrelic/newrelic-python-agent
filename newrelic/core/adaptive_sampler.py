class AdaptiveSampler(object):
    def __init__(self, sampling_target):
        self.min_sampling_priority = 0.0

        # For the first harvest, collect a max of sampling_target number of
        # "sampled" transactions.
        self.sampling_target = sampling_target
        self.max_sampled = sampling_target
        self.max_ratio = 0.5

        self.transaction_count = 0
        self.sampled_count = 0

    def compute_sampled(self, priority):
        if self.sampled_count >= self.max_sampled:
            return False

        elif priority >= self.min_sampling_priority:
            self.sampled_count += 1

            # Determine if a backoff is required and compute it
            target = self.sampling_target
            if self.sampled_count > target:
                ratio = target / float(self.sampled_count)
                target = target ** ratio - target ** self.max_ratio
                target = max(0.0, target)

                self._update_min_priority(target)

            return True

        return False

    def reset(self, transaction_count):
        # For subsequent harvests, collect a max of twice the
        # self._sampling_target value.
        self.max_sampled = 2 * self.sampling_target
        self.transaction_count = transaction_count
        self.sampled_count = 0
        self._update_min_priority(self.sampling_target)

    def _update_min_priority(self, target):
        if self.transaction_count > target:
            sampling_ratio = float(target) / self.transaction_count
            self.min_sampling_priority = 1.0 - sampling_ratio
        else:
            self.min_sampling_priority = 0.0
