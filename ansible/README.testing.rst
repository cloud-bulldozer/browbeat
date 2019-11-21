Running browebat ansible unit tests
===================================

Running ansible molecule unit tests
-----------------------------------

- Ensure that you have docker installed:

    https://docs.docker.com/install/

- Run tox -e molecule

Adding ansible molecue unit test
--------------------------------

- cd ansible/install/roles/<example role>
  molecule init scenario --role-name <example role> --driver-name docker
