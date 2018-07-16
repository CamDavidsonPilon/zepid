import warnings
import math 
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.genmod.families import family
from statsmodels.genmod.families import links
from zepid.causal.ipw import propensity_score

class SimpleDoublyRobust:
    '''Implementation of a simple doubly robust estimator as described in Funk et al. American Journal
    of Epidemiology 2011;173(7):761-767. The exact formulas used are available in Table 1 and Equation 1.
    Properties of the doubly robust estimator are often misunderstood, so we direct the reader to 
    Keil et al. AJE 2018;187(4):891-892. SimplyDoublyRobust only supports a binary exposure and binary
    outcome. Also this model does not deal with missing data or time varying exposures
    
    df:
        -pandas DataFrame object containing all variables of interest
    exposure:
        -column name of the exposure variable. Currently only binary is supported
    outcome:
        -column name of the outcome variable. Currently only binary is supported
    '''
    def __init__(self,df,exposure,outcome):
        self.df = df.copy()
        self._exposure = exposure
        self._outcome = outcome
        self._fit_exposure_model = False
        self._fit_outcome_model = False
        self._generated_ci = False
    
    def exposure_model(self,model,mresult=True):
        '''Used to specify the propensity score model. Model used to predict the exposure via a 
        logistic regression model
        
        model:
            -Independent variables to predict the exposure. Example) 'var1 + var2 + var3'
        mresult:
            -Whether to print the fitted model results. Default is True (prints results)
        '''
        self._exp_model = self._exposure + ' ~ '+ model
        self.df['ps'] = propensity_score(self.df,self._exp_model,mresult=mresult)
        self._fit_exposure_model = True
        
    def outcome_model(self,model,mresult=True):
        '''Used to specify the outcome model. Model used to predict the outcome via a logistic
        regression model
        
        model:
            -Independent variables to predict the outcome. Example) 'var1 + var2 + var3 + var4'
        mresult:
            -Whether to print the fitted model results. Default is True (prints results)
        '''

        self._out_model = self._outcome + ' ~ '+ model
        f = sm.families.family.Binomial(sm.families.links.logit) 
        log = smf.glm(self._out_model,self.df,family=f).fit()
        if mresult == True:
            print('\n----------------------------------------------------------------')
            print('MODEL: '+self._out_model)
            print('-----------------------------------------------------------------')
            print(log.summary())

        dfx = self.df.copy()
        dfx[self._exposure] = 1
        self.df['pY1'] = log.predict(dfx)
        dfx = self.df.copy()
        dfx[self._exposure] = 0
        self.df['pY0'] = log.predict(dfx)
        self._fit_outcome_model = True
    
    def fit(self):
        '''Once the exposure and outcome models are specified, we can estimate the Risk Ratio 
        and Risk Difference. This function generates the estimated risk difference and risk ratio. 
        To view results, use SimpleDoublyRobust.summary() For confidence intervals, bootstrap() must
        be run, otherwise only point estimates will be generated
        '''
        if ((self._fit_exposure_model == False) or (self._fit_exposure_model == False)):
            raise ValueError('The exposure and outcome models must be specified before the doubly robust estimate can be generated')
        
        #Doubly robust estimator for exposed
        self.df['dr1'] = np.where(self.df[self._exposure]==1,
                                  ((self.df[self._outcome])/self.df['ps']) - (((self.df['pY1'] * (1 - self.df['ps'])) / (self.df['ps']))),
                                  self.df['pY1'])
        
        #Doubly robust estimator for unexposed
        self.df['dr0'] = np.where(self.df[self._exposure]==0,
                                  (self.df['pY0']),
                                  ((self.df[self._outcome])/(1 - self.df['ps']) - (((self.df['pY0']) * (self.df['ps'])) / (1 - self.df['ps']))))
        
        #Generating estimates for the risk difference and risk ratio
        self.riskdiff = np.mean(self.df['dr1']) - np.mean(self.df['dr0'])
        self.riskratio = np.mean(self.df['dr1']) / np.mean(self.df['dr0'])
    
    def summary(self,decimal=4):
        '''Prints a summary of the results for the doubly robust estimator. 
        '''
        print('----------------------------------------------------------------------')
        print('Risk Difference: ',round(self.riskdiff,decimal))
        print('Risk Ratio: ',round(self.riskratio,decimal))
        print('----------------------------------------------------------------------')
