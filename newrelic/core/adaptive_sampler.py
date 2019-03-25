import random


class AdaptiveSampler(object):
    def __init__(self, sampling_target):
        self.adaptive_target = 0.0

        # For the first harvest, collect a max of sampling_target number of
        # "sampled" transactions.
        self.sampling_target = sampling_target
        self.max_sampled = sampling_target
        self.computed_count_last = sampling_target

        self.computed_count = 0
        self.sampled_count = 0

    def compute_sampled(self):
        if self.sampled_count >= self.max_sampled:
            return False

        elif self.sampled_count < self.sampling_target:
            sampled = random.randrange(
                    self.computed_count_last) < self.sampling_target
            if sampled:
                self.sampled_count += 1
        else:
            sampled = random.randrange(
                    self.computed_count) < self.adaptive_target
            if sampled:
                self.sampled_count += 1

                ratio = float(self.sampling_target) / self.sampled_count
                self.adaptive_target = (self.sampling_target ** ratio -
                                        self.sampling_target ** 0.5)

        self.computed_count += 1
        return sampled

    def reset(self):
        # For subsequent harvests, collect a max of twice the
        # self.sampling_target value.
        self.max_sampled = 2 * self.sampling_target
        self.adaptive_target = (self.sampling_target -
                                self.sampling_target ** 0.5)

        self.computed_count_last = max(self.computed_count,
                                       self.sampling_target)
        self.computed_count = 0
        self.sampled_count = 0
