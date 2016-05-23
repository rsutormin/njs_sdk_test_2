#BEGIN_HEADER
# The header block is where all import statments should live
import os
from pprint import pformat
from biokbase.workspace.client import Workspace as workspaceService  # @UnresolvedImport @IgnorePep8
from njs_sdk_test_2.GenericClient import GenericClient
import time
from multiprocessing.pool import ThreadPool, ApplyResult
import traceback
#END_HEADER


class njs_sdk_test_2:
    '''
    Module Name:
    njs_sdk_test

    Module Description:
    Module for testing NJSwrapper
    '''

    ######## WARNING FOR GEVENT USERS #######
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    #########################################
    VERSION = "0.0.1"
    GIT_URL = "https://github.com/kbasetest/njs_sdk_test_1"
    GIT_COMMIT_HASH = "f5b4986d4a2e7d6df1ff5794394e5c6c50b568a3"
    
    #BEGIN_CLASS_HEADER
    # Class variables and functions can be defined in this block
    def log(self, message, prefix_newline=False):
        mod = self.__class__.__name__
        print('{}{} {} ID: {}: {}'.format(
            ('\n' if prefix_newline else ''),
            str(time.time()), mod, self.id_, str(message)))
    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.workspaceURL = config['workspace-url']
        self.generic_clientURL = os.environ['SDK_CALLBACK_URL']
        self.id_ = None
        self.log('Callback URL: ' + self.generic_clientURL)
        #END_CONSTRUCTOR
        pass
    

    def run(self, ctx, params):
        # ctx is the context object
        # return variables are: results
        #BEGIN run
        mod = self.__class__.__name__
        self.id_ = params['id']
        self.log('Running commit {} with params:\n{}'.format(
            self.GIT_COMMIT_HASH, pformat(params)))
        token = ctx['token']
        run_jobs_async = params.get('run_jobs_async')

        wait_time = params.get('async_wait')
        if not wait_time:
            wait_time = 5000
        gc = GenericClient(self.generic_clientURL, use_url_lookup=False,
                           token=token, async_job_check_time_ms=wait_time)

        results = {'name': mod,
                   'hash': self.GIT_COMMIT_HASH,
                   'id': self.id_}
        if 'jobs' in params:
            jobs = params['jobs']
            self.log('Running jobs {}synchronously'.format(
                'a' if run_jobs_async else ''))
            if run_jobs_async:
                pool = ThreadPool(processes=len(jobs))

            def run_cli(p):
                async = p.get('cli_async')
                a = 'a' if async else ''
                self.log(('{}synchronous client run of method: {} ' +
                          'version: {} params:\n{}').format(
                          a, j['method'], j['ver'], pformat(j['params'])))
                if async:
                    ret = gc.asynchronous_call(
                        p['method'], p['params'], p['ver'])
                else:
                    ret = gc.sync_call(p['method'], p['params'], p['ver'])
                self.log('got back from {}sync:\n{}'.format(
                    a, pformat(ret)))
                return ret

            res = []
            for j in jobs:
                if run_jobs_async:
                    res.append(pool.apply_async(run_cli, (j,)))
                else:
                    res.append(run_cli(j))
            if run_jobs_async:
                pool.close()
                pool.join()
            try:
                res = [r.get() if type(r) == ApplyResult else r for r in res]
            except Exception as e:
                print('caught exception running jobs: ' + str(e))
                traceback.print_exc()
                raise
            self.log('got job results\n' + pformat(res))
            results['jobs'] = res
        if 'wait' in params:
            self.log('waiting for ' + str(params['wait']) + ' sec')
            time.sleep(params['wait'])
            results['wait'] = params['wait']
        if 'save' in params:
            gc = GenericClient(self.generic_clientURL, use_url_lookup=False,
                               token=token)
            prov = gc.sync_call("CallbackServer.get_provenance", [])[0]

            self.log('Saving workspace object\n' + pformat(results))
            self.log('with provenance\n' + pformat(prov))

            ws = workspaceService(self.workspaceURL, token=token)
            info = ws.save_objects({
                'workspace': params['save']['ws'],
                'objects': [
                    {
                     'type': 'Empty.AType',
                     'data': results,
                     'name': params['save']['name'],
                     'provenance': prov
                     }
                    ]
            })
            self.log('result:')
            self.log(info)
        if 'except' in params:
            raise ValueError(params.get('except') + ' ' + self.id_)
        #END run

        # At some point might do deeper type checking...
        if not isinstance(results, object):
            raise ValueError('Method run return value ' +
                             'results is not type object as required.')
        # return the results
        return [results]

    def status(self, ctx):
        #BEGIN_STATUS
        returnVal = {'state': "OK",
                     'message': "",
                     'version': self.VERSION,
                     'git_url': self.GIT_URL,
                     'git_commit_hash': self.GIT_COMMIT_HASH}
        del ctx  # shut up pep8
        #END_STATUS
        return [returnVal]
