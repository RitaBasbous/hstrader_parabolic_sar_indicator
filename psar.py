from collections import deque

class PSAR:
    def __init__(self, init_af=0.02, max_af=0.2, af_step=0.02):
        """
        Initialize the PSAR object with the given parameters.

        Parameters:
        - init_af (float): Initial acceleration factor.
        - max_af (float): Maximum acceleration factor.
        - af_step (float): Step by which the acceleration factor increases.
        """
        self.init_af = init_af
        self.max_af = max_af
        self.af_step = af_step
        self.reset()

    def reset(self):
        """
        Resets all internal states and lists used for calculation.
        """
        self.af = self.init_af
        self.extreme_point = None
        self.high_price_trend = []
        self.low_price_trend = []
        self.high_price_window = deque(maxlen=2)
        self.low_price_window = deque(maxlen=2)
        # Lists to track results
        self.psar_list = []
        self.af_list = []
        self.ep_list = []
        self.trend_list = []
        self._num_periods = 0
        self.trend = None

    def __init_psar_vals(self, high, low):
        """
        Initialize the PSAR values based on the first few data points.

        Parameters:
        - high (float): High price of the period.
        - low (float): Low price of the period.

        Returns:
        - float or None: Initial PSAR value or None if not enough data.
        """
        if len(self.low_price_window) <= 1:
            self.trend = None
            self.extreme_point = high
            return None

        if self.high_price_window[0] < self.high_price_window[1]:
            self.trend = 1
            psar = min(self.low_price_window)
            self.extreme_point = max(self.high_price_window)
        else:
            self.trend = 0
            psar = max(self.high_price_window)
            self.extreme_point = min(self.low_price_window)

        return psar

    def __calc_psar_val(self):
        """
        Calculate the PSAR based on the current trend and the most recent data.

        Returns:
        - float: Calculated PSAR value.
        """
        prev_psar = self.psar_list[-1]
        if self.trend == 1:  # Uptrend
            psar = prev_psar + self.af * (self.extreme_point - prev_psar)
            psar = min(psar, min(self.low_price_window))
        else:  # Downtrend
            psar = prev_psar - self.af * (prev_psar - self.extreme_point)
            psar = max(psar, max(self.high_price_window))

        return psar

    def __trend_reversal(self, psar, high, low):
        """
        Check for trend reversal and update values accordingly. If a reversal is detected, the trend and extreme point are updated,
        and the acceleration factor (af) is reset.

        Parameters:
        - psar (float): Current PSAR value.
        - high (float): High price of the period.
        - low (float): Low price of the period.

        Returns:
        - float: PSAR value after checking for trend reversal.
        """
        reversal = False
        if self.trend == 1 and psar > low:
            self.trend = 0
            psar = max(self.high_price_trend)
            self.extreme_point = low
            reversal = True
        elif self.trend == 0 and psar < high:
            self.trend = 1
            psar = min(self.low_price_trend)
            self.extreme_point = high
            reversal = True

        if reversal:
            self.af = self.init_af
            self.high_price_trend.clear()
            self.low_price_trend.clear()
        else:
            if high > self.extreme_point and self.trend == 1:
                self.af = min(self.af + self.af_step, self.max_af)
                self.extreme_point = high
            elif low < self.extreme_point and self.trend == 0:
                self.af = min(self.af + self.af_step, self.max_af)
                self.extreme_point = low

        return psar

    def __update_current_vals(self, psar, high, low):
        """
        Update the current values for PSAR calculation, track the results, and check for any trend reversals.

        Parameters:
        - psar (float): Current PSAR value.
        - high (float): High price of the period.
        - low (float): Low price of the period.

        Returns:
        - float: Updated PSAR value.
        """
        if self.trend == 1:
            self.high_price_trend.append(high)
        elif self.trend == 0:
            self.low_price_trend.append(low)

        psar = self.__trend_reversal(psar, high, low)

        self.psar_list.append(psar)
        self.af_list.append(self.af)
        self.ep_list.append(self.extreme_point)
        self.high_price_window.append(high)
        self.low_price_window.append(low)
        self.trend_list.append(self.trend)

        return psar

    def __calc_psar(self, high, low):
        """
        Calculates the PSAR value based on high and low prices.

        Parameters:
            high (float): High price for the current period.
            low (float): Low price for the current period.
            reset (bool): If True, reset the internal state before calculation.

        Returns:
            float: Calculated PSAR value.
        """
        
        if self._num_periods >= 3:
            psar = self.__calc_psar_val()
        else:
            psar = self.__init_psar_vals(high, low)

        psar = self.__update_current_vals(psar, high, low)
        self._num_periods += 1

        return psar
    def calc_psar_batch(self, highs, lows):
        """
        Calculate PSAR values for a batch of high and low prices.

        Parameters:
            highs (list): List of high prices.
            lows (list): List of low prices.

        Returns:
            list: List of calculated PSAR values.
        """
        self.reset()
        psar_values = []
        for high, low in zip(highs, lows):
            psar_values.append(self.__calc_psar(high, low))
        return psar_values