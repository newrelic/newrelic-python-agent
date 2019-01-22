#!/usr/bin/env bash

# Install asv
/venvs/py36/bin/pip install asv==0.3.0 virtualenv

cat <<EOF > ~/.asv-machine.json
{
    "$HOST_MACHINE": {
        "arch": "x86_64",
        "cpu": "",
        "machine": "$HOST_MACHINE",
        "os": "Linux",
        "ram": ""
    },
    "version": 1
}
EOF

# patch asv publish so that it has the command line option for no commit filter
cat <<EOF > ~/asv.patch
--- /venvs/py36/lib/python3.6/site-packages/asv/commands/publish.py.old	2018-10-01 11:40:12.000000000 -0700
+++ /venvs/py36/lib/python3.6/site-packages/asv/commands/publish.py	2018-10-01 11:40:21.000000000 -0700
@@ -59,6 +59,9 @@ class Publish(Command):
         parser.add_argument(
             '--no-pull', action='store_true', dest='no_pull',
             help="Do not pull the repository")
+        parser.add_argument(
+            '--no-commit-filtering', action='store_true', dest='no_commit_filtering',
+            help="Include all commits, instead of filtering. Default is 'False'.")
         parser.add_argument(
             'range', nargs='?', default=None,
             help="""Optional commit range to consider""")
@@ -75,7 +78,9 @@ class Publish(Command):
     def run_from_conf_args(cls, conf, args):
         if args.html_dir is not None:
             conf.html_dir = args.html_dir
-        return cls.run(conf=conf, range_spec=args.range, pull=not args.no_pull)
+
+        return cls.run(conf=conf, range_spec=args.range, pull=not args.no_pull,
+                        no_commit_filtering=args.no_commit_filtering)

     @staticmethod
     def iter_results(conf, repo, range_spec=None):
@@ -91,7 +96,7 @@ class Publish(Command):
                 yield result

     @classmethod
-    def run(cls, conf, range_spec=None, pull=True):
+    def run(cls, conf, range_spec=None, pull=True, no_commit_filtering=False):
         params = {}
         graphs = GraphSet()
         machines = {}
@@ -182,7 +187,7 @@ class Publish(Command):

                     for branch in [
                         branch for branch, commits in branches.items()
-                        if results.commit_hash in commits
+                        if (no_commit_filtering or results.commit_hash in commits) and (results.commit_hash in revisions)
                     ]:
                         cur_params = dict(results.params)
                         cur_params['branch'] = repo.get_branch_name(branch)
EOF

# apply the patch
patch -p0 -i ~/asv.patch /venvs/py36/lib/python3.6/site-packages/asv/commands/publish.py

/venvs/py36/bin/asv run HEAD~..HEAD
/venvs/py36/bin/asv publish --no-commit-filtering
